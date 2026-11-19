import asyncio
import logging
import time

from src.webhook.events import MergeRequestEvent, MREventAction
from src.gitlab.diff import build_diff_text, build_line_mapping
from src.gitlab.comments import post_pending_comment, update_review_comment, post_inline_comments, apply_review_labels, append_merge_notice
from src.ai.prompt import build_system_prompt, build_user_prompt
from src.ai.parser import parse_review_response
from src.skills.loader import SkillsLoader

logger = logging.getLogger(__name__)


REVIEW_TIMEOUT_SECONDS = 300  # 5 minutes


class WebhookHandler:
    """Process GitLab webhook events and trigger AI review."""

    def __init__(self, gitlab, ai_client, skills_loader: SkillsLoader):
        self.gitlab = gitlab
        self.ai_client = ai_client
        self.skills_loader = skills_loader

    async def handle(self, payload: dict) -> dict:
        """Main entry point for webhook events."""
        event = MergeRequestEvent.from_payload(payload)
        if event is None:
            return {"status": "skipped", "reason": "not a merge request"}

        # Only review on initial open or reopen
        if event.action not in (MREventAction.OPEN, MREventAction.REOPEN):
            logger.info(f"Skipping MR #{event.mr_iid} with action '{event.action.value}'")
            return {"status": "skipped", "reason": f"action={event.action.value}"}

        logger.info(f"Processing MR #{event.mr_iid} for project #{event.project_id}")
        t0 = time.time()

        # Post placeholder comment immediately
        try:
            note_id = post_pending_comment(self.gitlab, event.project_id, event.mr_iid)
            logger.info(f"[perf] placeholder comment: {time.time() - t0:.2f}s")
        except Exception:
            logger.exception("Failed to post placeholder comment, will post result directly")
            note_id = 0

        # Check for manual override
        if self.gitlab.has_manual_override(event.project_id, event.mr_iid):
            logger.info(f"Manual override detected for MR #{event.mr_iid}")
            if note_id:
                self.gitlab.update_mr_comment(event.project_id, event.mr_iid, note_id,
                                              "⏭️ **AI review skipped**\n\nThis MR is marked for manual review.")
            return {"status": "skipped", "reason": "manual override"}

        # Get MR diff
        t1 = time.time()
        diff_response = self.gitlab.get_mr_diff(event.project_id, event.mr_iid)
        diff = diff_response.get("changes", [])
        diff_refs = diff_response.get("diff_refs", {})
        shas = {
            "base_sha": diff_refs.get("base_sha", ""),
            "head_sha": diff_refs.get("head_sha", ""),
            "start_sha": diff_refs.get("start_sha", ""),
        }
        diff_text = build_diff_text(diff)
        deleted_files = {item["new_path"] for item in diff if item.get("deleted_file")}
        line_mapping, modified_lines = build_line_mapping(diff)
        logger.info(f"[perf] get_mr_diff ({len(diff)} changes, {len(diff_text)} chars): {time.time() - t1:.2f}s")
        if not diff_text:
            if note_id:
                self.gitlab.update_mr_comment(event.project_id, event.mr_iid, note_id,
                                              "⏭️ **AI review skipped**\n\nThis MR has no reviewable changes.")
            return {"status": "skipped", "reason": "no diff content"}

        # Load skills
        t2 = time.time()
        skills_loader = SkillsLoader(
            gitlab=self.gitlab,
            project_id=event.project_id,
            target_branch=event.target_branch,
            default_skills_dir=self.skills_loader.default_skills_dir,
        )
        skill_contents = await skills_loader.load_skills()
        if not skill_contents:
            skill_contents = skills_loader.load_default_skills(
                skills_loader.default_skills_dir
            )
        logger.info(f"[perf] load_skills ({len(skill_contents)} files): {time.time() - t2:.2f}s")

        # Check for skill changes in diff
        skill_changed = skills_loader.has_skill_changes(diff)

        # Build prompts and call AI
        system_prompt = build_system_prompt(skill_contents)
        user_prompt = build_user_prompt(event.title, diff_text)
        logger.info(f"[perf] build_prompts (sys={len(system_prompt)}, usr={len(user_prompt)} chars): {time.time() - t2:.2f}s")

        t3 = time.time()
        try:
            ai_response = await asyncio.wait_for(
                asyncio.to_thread(self.ai_client.review, system_prompt, user_prompt),
                timeout=REVIEW_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error(f"AI review timed out after {REVIEW_TIMEOUT_SECONDS}s for MR #{event.mr_iid}")
            if note_id:
                self.gitlab.update_mr_comment(
                    event.project_id, event.mr_iid, note_id,
                    f"⏱️ **AI review timed out**\n"
                    f"\n"
                    f"The review exceeded the {REVIEW_TIMEOUT_SECONDS // 60}-minute limit and could not be completed. Please try again later."
                )
            return {"status": "error", "reason": "timeout"}
        except Exception as e:
            logger.exception(f"AI review failed for MR #{event.mr_iid}: {e}")
            if note_id:
                self.gitlab.update_mr_comment(
                    event.project_id, event.mr_iid, note_id,
                    f"❌ **AI review failed**\n"
                    f"\n"
                    f"An error occurred while calling the AI model: `{e}`"
                )
            return {"status": "error", "reason": str(e)}
        logger.info(f"[perf] ai_review (resp={len(ai_response)} chars): {time.time() - t3:.2f}s")

        # Parse and post results
        t4 = time.time()
        review = parse_review_response(ai_response)
        logger.info(f"[perf] parse_review: {time.time() - t4:.2f}s")

        t5 = time.time()
        post_inline_comments(self.gitlab, event.project_id, event.mr_iid, review, shas, line_mapping, modified_lines, deleted_files)
        update_review_comment(self.gitlab, event.project_id, event.mr_iid, note_id, review)
        apply_review_labels(self.gitlab, event.project_id, event.mr_iid, review, skill_changed)
        logger.info(f"[perf] update_comment+labels: {time.time() - t5:.2f}s")

        # Auto-merge if review passed with no issues
        if review.status == "Pass" and not skill_changed and not review.comments:
            try:
                mr_info = self.gitlab.get_mr_info(event.project_id, event.mr_iid)
                self.gitlab.accept_mr(event.project_id, event.mr_iid, mr_info.get("sha", ""))
                logger.info(f"Auto-merged MR #{event.mr_iid}")
                if note_id:
                    append_merge_notice(self.gitlab, event.project_id, event.mr_iid, note_id)
            except Exception:
                logger.exception(f"Auto-merge failed for MR #{event.mr_iid}")

        logger.info(f"[perf] TOTAL: {time.time() - t0:.2f}s")

        return {
            "status": "completed",
            "score": review.score,
            "review_status": review.status,
            "comments_count": len(review.comments),
            "skill_changed": skill_changed,
        }

    def handle_sync(self, payload: dict) -> dict:
        """Synchronous wrapper for handle() — runs in background thread."""
        try:
            return asyncio.run(self.handle(payload))
        except Exception as e:
            logger.exception(f"Webhook processing failed: {e}")
            return {"status": "error", "message": str(e)}

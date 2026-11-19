AI_LABEL_PREFIX = "AI-Review:"

import logging

ALL_AI_LABELS = [
    "AI-Review: Passed",
    "AI-Review: Needs Revision",
    "AI-Review: Skill Changed",
    "AI-Review: Needs Human Review",
]


from src.gitlab.client import GitLabClient


def post_pending_comment(client: GitLabClient, project_id: int, mr_iid: int) -> int:
    """Post a 'reviewing in progress' placeholder comment. Returns note ID."""
    body = (
        "🤖 **AI is reviewing this MR, please wait...**\n"
        "\n"
        "This comment will be automatically updated with the results once the review is complete."
    )
    return client.post_mr_comment(project_id, mr_iid, body)


def update_review_comment(client: GitLabClient, project_id: int, mr_iid: int,
                          note_id: int, review):
    """Update the placeholder comment with the actual review results.

    If note_id is 0 (no placeholder was posted), posts a new comment instead.
    """
    if not review.comments:
        body = _build_summary_comment(review, [])
    else:
        # Group by (file, line)
        grouped: dict[tuple[str, int], list] = {}
        for comment in review.comments:
            key = (comment.file, comment.line)
            grouped.setdefault(key, []).append(comment)

        # Sort by line number
        sorted_groups = sorted(grouped.items(), key=lambda kv: kv[0][1])

        lines = []
        for (file_path, line), comments in sorted_groups:
            lines.append(f"### `{file_path}` line {line}")
            for i, c in enumerate(comments, 1):
                if i > 1:
                    lines.append("")
                lines.append(f"**{i}. Problem:** {c.problem}")
                lines.append("")
                lines.append(f"**Suggestion:** {c.suggestion}")
            lines.append("")

        body = _build_summary_comment(review, lines)

    try:
        if note_id:
            client.update_mr_comment(project_id, mr_iid, note_id, body)
        else:
            client.post_mr_comment(project_id, mr_iid, body)
    except Exception:
        # Fallback: try the other approach if one fails
        try:
            if note_id:
                client.post_mr_comment(project_id, mr_iid, body)
            else:
                client.update_mr_comment(project_id, mr_iid, note_id, body)
        except Exception:
            pass


def _build_summary_comment(review, detail_lines: list[str]) -> str:
    """Build the full MR-level summary comment."""
    status_emoji = "✅" if review.status == "Pass" else "⚠️"
    parts = [
        f"# AI Review Report",
        f"",
        f"**Score:** {review.score}/100",
        f"**Status:** {status_emoji} {review.status}",
        f"",
    ]
    if detail_lines:
        parts.append("---")
        parts.append("")
        parts.extend(detail_lines)
    else:
        parts.append("No issues found.")
    return "\n".join(parts)


def append_merge_notice(client: GitLabClient, project_id: int, mr_iid: int, note_id: int):
    """Append an auto-merge notice to an existing review comment."""
    if not note_id:
        return
    merge_body = (
        "\n\n---\n\n"
        "🚀 **AI review passed, auto-merged.**"
    )
    try:
        # Fetch the current comment body and append the merge notice
        url = client._api_url(f"projects/{project_id}/merge_requests/{mr_iid}/notes/{note_id}")
        import httpx
        resp = client._http.get(url)
        if resp.status_code == 200:
            current_body = resp.json().get("body", "")
            client.update_mr_comment(project_id, mr_iid, note_id, current_body + merge_body)
    except Exception:
        pass


def apply_review_labels(client, project_id: int, mr_iid: int, review, skill_changed: bool):
    """Apply appropriate AI-Review labels based on review result."""
    current_labels = client.get_mr_labels(project_id, mr_iid)

    # Remove all existing AI labels
    for label in ALL_AI_LABELS:
        if label in current_labels:
            client.remove_label(project_id, mr_iid, label)

    # Skip labeling if manual override is present
    if "AI-Review: Manual Override" in current_labels:
        return

    # Add review result label
    if review.status == "Pass" and not skill_changed:
        client.add_label(project_id, mr_iid, "AI-Review: Passed")
    elif skill_changed:
        client.add_label(project_id, mr_iid, "AI-Review: Needs Revision")
        client.add_label(project_id, mr_iid, "AI-Review: Skill Changed")
        client.add_label(project_id, mr_iid, "AI-Review: Needs Human Review")
    else:
        client.add_label(project_id, mr_iid, "AI-Review: Needs Revision")


def post_inline_comments(client, project_id: int, mr_iid: int,
                         review, shas: dict,
                         line_mapping: dict[str, dict[int, int | None]] | None = None,
                         modified_lines: dict[str, set[int]] | None = None,
                         deleted_files: set | None = None) -> tuple[int, int]:
    """Post each review comment as an inline diff comment on the MR Changes tab.

    Multiple issues on the same line are merged into a single inline comment.
    Returns (posted_count, failed_count).

    GitLab requires different line_code handling per line type:
    - Context lines: old_line (int) + line_code works
    - Modified lines: old_line='' (empty str) + line_code works
    - Pure additions: no old_line, no line_code works
    """
    if deleted_files is None:
        deleted_files = set()
    if line_mapping is None:
        line_mapping = {}
    if modified_lines is None:
        modified_lines = {}

    # Group comments by (file, line)
    grouped: dict[tuple[str, int], list] = {}
    for comment in review.comments:
        key = (comment.file, comment.line)
        grouped.setdefault(key, []).append(comment)

    posted = 0
    failed = 0
    for (file_path, line), comments in grouped.items():
        if file_path in deleted_files:
            continue

        file_lines = line_mapping.get(file_path, {}) if line_mapping else {}
        is_modified = line in modified_lines.get(file_path, set())

        # If line mapping is available but line not found in diff, skip
        if line_mapping and line not in file_lines:
            continue

        old_line = file_lines.get(line)
        # Build combined body for multiple issues on the same line
        if len(comments) == 1:
            body = f"**Problem:** {comments[0].problem}\n\n**Suggestion:** {comments[0].suggestion}"
        else:
            parts = []
            for i, c in enumerate(comments, 1):
                parts.append(f"**{i}. Problem:** {c.problem}")
                parts.append(f"\n**Suggestion:** {c.suggestion}")
            body = "\n\n".join(parts)

        try:
            client.post_line_comment(
                project_id, mr_iid,
                file_path, line, body,
                old_line=old_line if not is_modified else "",
                is_modified=is_modified,
                **shas,
            )
            posted += 1
        except Exception:
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Failed to post inline comment on {file_path}:{line}",
                exc_info=True,
            )
            failed += 1

    return posted, failed

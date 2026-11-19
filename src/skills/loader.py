import glob
import os
from pathlib import Path


class SkillsLoader:
    SKILLS_PREFIX = ".ai-review/skills/"

    def __init__(
        self,
        gitlab,
        project_id: int,
        target_branch: str,
        default_skills_dir: str,
    ):
        self.gitlab = gitlab
        self.project_id = project_id
        self.target_branch = target_branch
        self.default_skills_dir = Path(default_skills_dir)

    async def load_skills(self) -> list[str]:
        """Load skill files from target branch.
        Returns empty list if no project skills (caller uses defaults).
        """
        skill_files = await self._list_project_skills()
        if not skill_files:
            return []

        contents = []
        for path in skill_files:
            content = self.gitlab.get_file_content(
                self.project_id, path, self.target_branch
            )
            if content:
                contents.append(content)
        return contents

    async def _list_project_skills(self) -> list[str]:
        """List .md files under .ai-review/skills/ on target branch."""
        tree = self.gitlab.list_tree(
            self.project_id, self.SKILLS_PREFIX, self.target_branch
        )
        return [item["path"] for item in tree if item["path"].endswith(".md")]

    def has_skill_changes(self, diff: list[dict]) -> bool:
        """Check if any diff touches .ai-review/skills/."""
        for item in diff:
            old_path = item.get("old_path", "")
            new_path = item.get("new_path", "")
            if old_path.startswith(self.SKILLS_PREFIX) or new_path.startswith(self.SKILLS_PREFIX):
                return True
        return False

    @staticmethod
    def load_default_skills(skills_dir: Path) -> list[str]:
        """Load all .md files from default-skills directory."""
        if not skills_dir.exists():
            return []
        paths = sorted(glob.glob(str(skills_dir / "*.md")))
        contents = []
        for path in paths:
            with open(path, "r", encoding="utf-8") as f:
                contents.append(f.read())
        return contents

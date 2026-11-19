import pytest
from src.skills.loader import SkillsLoader


class FakeGitLabDiff:
    """Mock GitLab diff API for testing."""

    def __init__(self, diff=None, file_contents=None):
        self.diff = diff or []
        self.file_contents = file_contents or {}

    def get_file_content(self, project_id: int, file_path: str, ref: str) -> str | None:
        return self.file_contents.get(file_path)

    def list_tree(self, project_id: int, prefix: str, ref: str) -> list[dict]:
        results = []
        for path in self.file_contents:
            if path.startswith(prefix):
                results.append({"path": path})
        return results


@pytest.mark.asyncio
async def test_load_default_skills_when_no_project_skills():
    loader = SkillsLoader(
        gitlab=FakeGitLabDiff(),
        project_id=100,
        target_branch="main",
        default_skills_dir="default-skills",
    )
    # With no project skills, should return empty list (default skills loaded separately)
    skills = await loader.load_skills()
    assert skills == []


@pytest.mark.asyncio
async def test_load_project_skills_from_target_branch():
    loader = SkillsLoader(
        gitlab=FakeGitLabDiff(
            file_contents={
                ".ai-review/skills/security.md": "Security rules here",
                ".ai-review/skills/custom.md": "Custom rules",
            }
        ),
        project_id=100,
        target_branch="main",
        default_skills_dir="default-skills",
    )
    skills = await loader.load_skills()
    assert len(skills) == 2
    assert "Security rules here" in skills[0]
    assert "Custom rules" in skills[1]


@pytest.mark.asyncio
async def test_detect_skill_file_changes_in_diff():
    loader = SkillsLoader(
        gitlab=FakeGitLabDiff(),
        project_id=100,
        target_branch="main",
        default_skills_dir="default-skills",
    )
    diff_with_skill_changes = [
        {
            "new_path": ".ai-review/skills/new.md",
            "new_file": True,
            "diff": "+++",
        },
        {
            "old_path": "src/main.py",
            "new_path": "src/main.py",
            "new_file": False,
            "diff": "@@ -1,3 +1,5 @@",
        },
    ]
    assert loader.has_skill_changes(diff_with_skill_changes) is True


@pytest.mark.asyncio
async def test_no_skill_file_changes():
    loader = SkillsLoader(
        gitlab=FakeGitLabDiff(),
        project_id=100,
        target_branch="main",
        default_skills_dir="default-skills",
    )
    diff_without_skill_changes = [
        {
            "old_path": "src/main.py",
            "new_path": "src/main.py",
            "new_file": False,
            "diff": "@@ -1,3 +1,5 @@",
        },
    ]
    assert loader.has_skill_changes(diff_without_skill_changes) is False

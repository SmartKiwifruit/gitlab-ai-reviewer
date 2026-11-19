import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.webhook.handler import WebhookHandler
from src.webhook.events import MREventAction


@pytest.fixture
def mock_components():
    gitlab = MagicMock()
    gitlab.get_mr_info.return_value = {
        "title": "Test MR",
        "target_branch": "main",
        "source_branch": "feature-1",
        "labels": [],
    }
    gitlab.get_mr_diff.return_value = {
        "base_commit_sha": "base123",
        "head_commit_sha": "head456",
        "start_commit_sha": "start789",
        "changes": [
            {"old_path": "a.py", "new_path": "a.py", "diff": "+line", "new_file": False, "deleted_file": False, "renamed_file": False}
        ]
    }
    gitlab.get_mr_labels.return_value = []
    gitlab.has_manual_override.return_value = False
    gitlab.get_file_content.return_value = None
    gitlab.list_tree.return_value = []

    ai_client = MagicMock()
    ai_client.review.return_value = "## Review Summary\n- Score: 90\n- Status: Pass\n\n## Comments\n"

    loader = MagicMock()
    loader.load_skills = AsyncMock(return_value=[])
    loader.has_skill_changes.return_value = False
    loader.load_default_skills.return_value = ["default skill content"]
    loader.default_skills_dir = "/fake/default-skills"

    return {"gitlab": gitlab, "ai_client": ai_client, "loader": loader}


@pytest.mark.asyncio
async def test_handle_open_mr(mock_components, sample_mr_payload):
    with patch("src.webhook.handler.SkillsLoader") as MockSkillsLoader:
        mock_loader = MagicMock()
        mock_loader.load_skills = AsyncMock(return_value=[])
        mock_loader.has_skill_changes.return_value = False
        mock_loader.load_default_skills.return_value = ["default skill content"]
        mock_loader.default_skills_dir = "/fake/default-skills"
        MockSkillsLoader.return_value = mock_loader

        mock_components["loader"].default_skills_dir = "/fake/default-skills"
        handler = WebhookHandler(
            gitlab=mock_components["gitlab"],
            ai_client=mock_components["ai_client"],
            skills_loader=mock_components["loader"],
        )
        await handler.handle(sample_mr_payload)
    mock_components["ai_client"].review.assert_called_once()
    mock_components["gitlab"].add_label.assert_called()


@pytest.mark.asyncio
async def test_handle_manual_override_skips(mock_components, sample_mr_payload):
    mock_components["gitlab"].has_manual_override.return_value = True
    handler = WebhookHandler(
        gitlab=mock_components["gitlab"],
        ai_client=mock_components["ai_client"],
        skills_loader=mock_components["loader"],
    )
    await handler.handle(sample_mr_payload)
    mock_components["ai_client"].review.assert_not_called()


@pytest.mark.asyncio
async def test_handle_non_mr_event():
    payload = {"object_kind": "push"}
    handler = WebhookHandler(gitlab=MagicMock(), ai_client=MagicMock(), skills_loader=MagicMock())
    result = await handler.handle(payload)
    assert result == {"status": "skipped", "reason": "not a merge request"}


@pytest.mark.asyncio
async def test_handle_skill_changes(mock_components, sample_mr_payload):
    with patch("src.webhook.handler.SkillsLoader") as MockSkillsLoader:
        mock_loader = MagicMock()
        mock_loader.load_skills = AsyncMock(return_value=[])
        mock_loader.has_skill_changes.return_value = True
        mock_loader.load_default_skills.return_value = ["default skill content"]
        mock_loader.default_skills_dir = "/fake/default-skills"
        MockSkillsLoader.return_value = mock_loader

        mock_components["loader"].default_skills_dir = "/fake/default-skills"
        handler = WebhookHandler(
            gitlab=mock_components["gitlab"],
            ai_client=mock_components["ai_client"],
            skills_loader=mock_components["loader"],
        )
        await handler.handle(sample_mr_payload)
    # Should still call AI but also add skill-changed labels
    mock_components["ai_client"].review.assert_called_once()
    mock_components["gitlab"].add_label.assert_any_call(100, 42, "AI-Review: Skill Changed")


def test_webhook_receives_event():
    """Test webhook endpoint accepts MR payload."""
    from fastapi.testclient import TestClient
    from src.main import create_app

    mock_gitlab = MagicMock()
    mock_gitlab.has_manual_override.return_value = False
    mock_gitlab.get_mr_diff.return_value = {
        "base_commit_sha": "base123",
        "head_commit_sha": "head456",
        "start_commit_sha": "start789",
        "changes": [
            {"old_path": "a.py", "new_path": "a.py", "diff": "+line", "new_file": False, "deleted_file": False, "renamed_file": False}
        ]
    }
    mock_gitlab.get_mr_labels.return_value = []

    mock_ai = MagicMock()
    mock_ai.review.return_value = "## Review Summary\n- Score: 90\n- Status: Pass\n\n## Comments\n"

    mock_loader = MagicMock()
    mock_loader.load_skills = AsyncMock(return_value=[])
    mock_loader.has_skill_changes.return_value = False
    mock_loader.load_default_skills.return_value = []
    mock_loader.default_skills_dir = "/fake/default-skills"

    app = create_app(
        gitlab_client=mock_gitlab,
        ai_client=mock_ai,
        skills_loader=mock_loader,
    )
    client = TestClient(app)

    response = client.post("/webhook", json={
        "object_kind": "merge_request",
        "object_attributes": {
            "iid": 42,
            "action": "open",
            "target_branch": "main",
            "source_branch": "feature-1",
            "title": "Test MR",
            "state": "opened",
        },
        "project": {"id": 100},
    })
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

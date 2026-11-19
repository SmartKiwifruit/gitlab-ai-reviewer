import pytest
from unittest.mock import MagicMock
from src.gitlab.client import GitLabClient
from src.gitlab.diff import build_diff_text
from src.gitlab.comments import apply_review_labels
from src.ai.parser import ReviewResult, ReviewComment, Severity


@pytest.fixture
def mock_httpx():
    client = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"id": 100, "title": "Test MR"}
    client.get.return_value = response
    client.post.return_value = response
    return client


def test_get_mr_info(mock_httpx):
    client = GitLabClient("http://gitlab.test", "test-token", httpx_client=mock_httpx)
    mr = client.get_mr_info(100, 42)
    assert mr["id"] == 100
    mock_httpx.get.assert_called_once()
    assert "merge_requests/42" in str(mock_httpx.get.call_args)


def test_get_mr_diff(mock_httpx):
    mock_httpx.get.return_value.json.return_value = {
        "base_commit_sha": "abc123",
        "head_commit_sha": "def456",
        "start_commit_sha": "ghi789",
        "changes": [
            {"old_path": "a.py", "new_path": "a.py", "diff": "+line"}
        ]
    }
    client = GitLabClient("http://gitlab.test", "test-token", httpx_client=mock_httpx)
    result = client.get_mr_diff(100, 42)
    assert result["base_commit_sha"] == "abc123"
    assert result["head_commit_sha"] == "def456"
    assert result["start_commit_sha"] == "ghi789"
    assert len(result["changes"]) == 1
    assert result["changes"][0]["old_path"] == "a.py"


def test_add_label(mock_httpx):
    client = GitLabClient("http://gitlab.test", "test-token", httpx_client=mock_httpx)
    client.add_label(100, 42, "AI-Review: Passed")
    mock_httpx.put.assert_called_once()


def test_remove_label(mock_httpx):
    client = GitLabClient("http://gitlab.test", "test-token", httpx_client=mock_httpx)
    client.remove_label(100, 42, "AI-Review: Passed")
    mock_httpx.put.assert_called_once()


def test_get_mr_labels(mock_httpx):
    mock_httpx.get.return_value.json.return_value = {"labels": ["bug", "AI-Review: Passed"]}
    client = GitLabClient("http://gitlab.test", "test-token", httpx_client=mock_httpx)
    labels = client.get_mr_labels(100, 42)
    assert "AI-Review: Passed" in labels


def test_post_line_comment(mock_httpx):
    client = GitLabClient("http://gitlab.test", "test-token", httpx_client=mock_httpx)
    client.post_line_comment(100, 42, "a.py", 10, "test comment")
    mock_httpx.post.assert_called_once()


def test_has_manual_override_label(mock_httpx):
    mock_httpx.get.return_value.json.return_value = {"labels": ["AI-Review: Manual Override"]}
    client = GitLabClient("http://gitlab.test", "test-token", httpx_client=mock_httpx)
    assert client.has_manual_override(100, 42) is True


def test_no_manual_override_label(mock_httpx):
    mock_httpx.get.return_value.json.return_value = {"labels": ["bug"]}
    client = GitLabClient("http://gitlab.test", "test-token", httpx_client=mock_httpx)
    assert client.has_manual_override(100, 42) is False


def test_build_diff_text_simple():
    diff = [
        {
            "old_path": "a.py",
            "new_path": "a.py",
            "new_file": False,
            "diff": "@@ -1,3 +1,5 @@\n line1\n+new line\n",
        },
    ]
    text = build_diff_text(diff)
    assert "a.py" in text
    assert "+new line" in text


def test_build_diff_text_empty():
    text = build_diff_text([])
    assert text == ""


def test_build_diff_text_new_file():
    diff = [
        {
            "old_path": "/dev/null",
            "new_path": "new.py",
            "new_file": True,
            "diff": "+print('hello')\n",
        },
    ]
    text = build_diff_text(diff)
    assert "new.py" in text


def test_apply_review_labels_pass():
    mock_client = MagicMock()
    mock_client.get_mr_labels.return_value = []
    result = ReviewResult(score=90, status="Pass", comments=[])
    skill_changed = False
    apply_review_labels(mock_client, 100, 42, result, skill_changed)
    mock_client.add_label.assert_called_with(100, 42, "AI-Review: Passed")
    mock_client.remove_label.assert_not_called()


def test_apply_review_labels_needs_revision():
    mock_client = MagicMock()
    mock_client.get_mr_labels.return_value = ["AI-Review: Passed"]
    result = ReviewResult(
        score=30,
        status="Needs Revision",
        comments=[ReviewComment("a.py", 1, Severity.CRITICAL, "bug", "fix")],
    )
    skill_changed = False
    apply_review_labels(mock_client, 100, 42, result, skill_changed)
    mock_client.remove_label.assert_called_with(100, 42, "AI-Review: Passed")
    mock_client.add_label.assert_any_call(100, 42, "AI-Review: Needs Revision")


def test_apply_review_labels_skill_changed():
    mock_client = MagicMock()
    mock_client.get_mr_labels.return_value = []
    result = ReviewResult(score=90, status="Pass", comments=[])
    skill_changed = True
    apply_review_labels(mock_client, 100, 42, result, skill_changed)
    mock_client.add_label.assert_any_call(100, 42, "AI-Review: Skill Changed")
    mock_client.add_label.assert_any_call(100, 42, "AI-Review: Needs Human Review")


from src.gitlab.comments import post_inline_comments


def test_post_inline_comments_posts_each_comment():
    mock_client = MagicMock()
    review = ReviewResult(
        score=50,
        status="Needs Revision",
        comments=[
            ReviewComment("a.py", 10, Severity.CRITICAL, "SQL injection", "Use params"),
            ReviewComment("b.py", 5, Severity.WARNING, "Hardcoded value", "Extract constant"),
        ],
    )
    shas = {"base_sha": "a", "head_sha": "b", "start_sha": "c"}
    posted, failed = post_inline_comments(mock_client, 100, 42, review, shas)
    assert posted == 2
    assert failed == 0
    assert mock_client.post_line_comment.call_count == 2


def test_post_inline_comments_skips_deleted_files():
    mock_client = MagicMock()
    review = ReviewResult(
        score=70,
        status="Needs Revision",
        comments=[
            ReviewComment("old.py", 3, Severity.WARNING, "issue", "fix"),
        ],
    )
    shas = {"base_sha": "a", "head_sha": "b", "start_sha": "c"}
    posted, failed = post_inline_comments(mock_client, 100, 42, review, shas, deleted_files={"old.py"})
    assert posted == 0
    mock_client.post_line_comment.assert_not_called()


def test_post_inline_comments_handles_failure_gracefully():
    mock_client = MagicMock()
    mock_client.post_line_comment.side_effect = [Exception("API error"), None]
    review = ReviewResult(
        score=50,
        status="Needs Revision",
        comments=[
            ReviewComment("a.py", 10, Severity.CRITICAL, "prob1", "sug1"),
            ReviewComment("b.py", 5, Severity.WARNING, "prob2", "sug2"),
        ],
    )
    shas = {"base_sha": "a", "head_sha": "b", "start_sha": "c"}
    posted, failed = post_inline_comments(mock_client, 100, 42, review, shas)
    assert posted == 1
    assert failed == 1


def test_post_inline_comments_empty_review():
    mock_client = MagicMock()
    review = ReviewResult(score=100, status="Pass", comments=[])
    shas = {"base_sha": "a", "head_sha": "b", "start_sha": "c"}
    posted, failed = post_inline_comments(mock_client, 100, 42, review, shas)
    assert posted == 0
    assert failed == 0
    mock_client.post_line_comment.assert_not_called()

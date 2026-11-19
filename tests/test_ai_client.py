import pytest
from unittest.mock import MagicMock
from src.ai.client import AIClient


@pytest.fixture
def mock_httpx():
    return MagicMock()


def test_claude_provider(mock_httpx):
    mock_httpx.post.return_value.json.return_value = {
        "content": [{"text": "## Review Summary\n- Score: 90\n- Status: Pass\n\n## Comments\n"}]
    }
    client = AIClient(provider="claude", api_key="test-key", model="claude-sonnet-4-6", httpx_client=mock_httpx)
    result = client.review("system prompt", "user prompt")
    assert "Review Summary" in result
    mock_httpx.post.assert_called_once()
    call_kwargs = mock_httpx.post.call_args[1]
    assert "claude" in call_kwargs["json"]["model"]


def test_openai_provider(mock_httpx):
    mock_httpx.post.return_value.json.return_value = {
        "choices": [{"message": {"content": "## Review Summary\n- Score: 90\n- Status: Pass\n\n## Comments\n"}}]
    }
    client = AIClient(provider="openai", api_key="test-key", model="gpt-4", httpx_client=mock_httpx)
    result = client.review("system prompt", "user prompt")
    assert "Review Summary" in result


def test_qwen_provider(mock_httpx):
    mock_httpx.post.return_value.json.return_value = {
        "output": {"text": "## Review Summary\n- Score: 90\n- Status: Pass\n\n## Comments\n"}
    }
    client = AIClient(provider="qwen", api_key="test-key", model="qwen-plus", httpx_client=mock_httpx)
    result = client.review("system prompt", "user prompt")
    assert "Review Summary" in result


def test_unknown_provider_raises_error():
    with pytest.raises(ValueError, match="Unknown provider"):
        AIClient(provider="unknown", api_key="test-key", model="test")

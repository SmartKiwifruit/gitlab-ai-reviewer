from src.ai.prompt import build_system_prompt, build_user_prompt


def test_build_system_prompt_with_skills():
    skills = ["Rule 1: Check security", "Rule 2: Check quality"]
    prompt = build_system_prompt(skills)
    assert "Rule 1: Check security" in prompt
    assert "Rule 2: Check quality" in prompt
    assert "English" in prompt  # English output requirement


def test_build_system_prompt_without_skills():
    prompt = build_system_prompt([])
    assert "review" in prompt.lower()  # Default review instruction
    assert "English" in prompt


def test_build_user_prompt_with_diff():
    diff_text = "+new line\n-old line"
    mr_title = "Fix auth bug"
    prompt = build_user_prompt(mr_title, diff_text)
    assert "Fix auth bug" in prompt
    assert diff_text in prompt

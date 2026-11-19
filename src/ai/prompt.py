SYSTEM_PROMPT_HEADER = """You are a senior code reviewer. Review the code changes in the following GitLab Merge Request.

## Output Requirements
- All comments and explanations must be written in English
- Report only real issues; do not comment for the sake of commenting
- Ignore style/formatting issues (unless they severely hurt readability)
"""

SYSTEM_PROMPT_SKILLS_DIRECTIVE = """
## Important
- Check **only** against the "Review Rules" specified below
- Do **not** extend the review scope on your own; do not report issues outside the rules
- If a problem type is not mentioned in the rules, do not report it even if it exists in the code
"""

SYSTEM_PROMPT_FORMAT_INSTRUCTIONS = """
## Output Format

Follow this format strictly:

## Review Summary
- Score: <number 0-100>
- Status: Pass or Needs Revision

## Comments
[FILE:<file path>, LINE:<line number>, SEVERITY:<critical|warning|info>]
Problem: <problem description>
Suggestion: <suggested fix>

One block per comment. If there are no issues, leave the Comments section empty.

SEVERITY levels:
- critical: security vulnerabilities, serious bugs, issues that cause runtime errors
- warning: potential risks, performance issues, maintainability issues
- info: suggestions, non-critical improvements
"""


def build_system_prompt(skills: list[str]) -> str:
    """Build system prompt by combining header, skills, and format instructions."""
    parts = [SYSTEM_PROMPT_HEADER]

    if skills:
        parts.append(SYSTEM_PROMPT_SKILLS_DIRECTIVE)
        parts.append("## Review Rules\n")
        for skill in skills:
            parts.append(skill)
            parts.append("")
    else:
        parts.append("Apply general code review standards.")

    parts.append(SYSTEM_PROMPT_FORMAT_INSTRUCTIONS)
    return "\n".join(parts)


def build_user_prompt(mr_title: str, diff_text: str) -> str:
    """Build user prompt with MR title and diff content."""
    return f"""## Merge Request
Title: {mr_title}

## Code Diff
{diff_text}

Please review the changes above."""

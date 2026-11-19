from src.ai.parser import parse_review_response, ReviewResult, Severity


def test_parse_full_response():
    response = """## Review Summary
- Score: 75/100
- Status: Needs Revision

## Comments
[FILE:src/user.py, LINE:42, SEVERITY:critical]
Problem: SQL injection risk
Suggestion: Use parameterized queries

[FILE:src/handler.py, LINE:15, SEVERITY:warning]
Problem: Function is too long
Suggestion: Split into smaller functions
"""
    result = parse_review_response(response)
    assert result.score == 75
    assert result.status == "Needs Revision"
    assert len(result.comments) == 2
    assert result.comments[0].file == "src/user.py"
    assert result.comments[0].line == 42
    assert result.comments[0].severity == Severity.CRITICAL
    assert "SQL injection" in result.comments[0].problem
    assert result.comments[1].severity == Severity.WARNING


def test_parse_pass_response():
    response = """## Review Summary
- Score: 95/100
- Status: Pass

## Comments
"""
    result = parse_review_response(response)
    assert result.status == "Pass"
    assert len(result.comments) == 0


def test_parse_response_with_missing_fields():
    response = """## Review Summary
- Score: 80/100
- Status: Pass

## Comments
[FILE:src/main.py, LINE:10, SEVERITY:critical]
Problem: Missing error handling
Suggestion: Add try-except
"""
    result = parse_review_response(response)
    assert result.score == 80
    assert len(result.comments) == 1


def test_parse_malformed_response_fallback():
    """If response doesn't match expected format, return safe defaults."""
    response = "The code looks good to me. No issues found."
    result = parse_review_response(response)
    assert result.score == 50  # Default score for unparseable
    assert result.status == "Pass"  # Safe default
    assert result.comments == []

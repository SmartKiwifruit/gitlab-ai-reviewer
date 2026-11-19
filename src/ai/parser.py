import re
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ReviewComment:
    file: str
    line: int
    severity: Severity
    problem: str
    suggestion: str


@dataclass
class ReviewResult:
    score: int
    status: str  # "Pass" or "Needs Revision"
    comments: list[ReviewComment] = field(default_factory=list)


_SCORE_RE = re.compile(r"Score:\s*(\d+)")
_STATUS_RE = re.compile(r"Status:\s*(Pass|Needs Revision)")
_COMMENT_BLOCK_RE = re.compile(
    r"\[FILE:(?P<file>[^,\]]+),\s*LINE:(?P<line>\d+),\s*SEVERITY:(?P<severity>\w+)\]\s*\n"
    r"Problem:\s*(?P<problem>[^\n]+)\n"
    r"Suggestion:\s*(?P<suggestion>[^\n]*)",
    re.MULTILINE,
)


def parse_review_response(response: str) -> ReviewResult:
    """Parse AI's structured review response into ReviewResult."""
    score_match = _SCORE_RE.search(response)
    status_match = _STATUS_RE.search(response)

    score = int(score_match.group(1)) if score_match else 50
    status = status_match.group(1) if status_match else "Pass"

    comments = []
    for match in _COMMENT_BLOCK_RE.finditer(response):
        try:
            severity = Severity(match.group("severity").lower())
        except ValueError:
            severity = Severity.INFO

        comments.append(ReviewComment(
            file=match.group("file").strip(),
            line=int(match.group("line")),
            severity=severity,
            problem=match.group("problem").strip(),
            suggestion=match.group("suggestion").strip(),
        ))

    return ReviewResult(score=score, status=status, comments=comments)

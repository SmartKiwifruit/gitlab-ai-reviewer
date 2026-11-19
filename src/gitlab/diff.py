import re


def build_diff_text(diff: list[dict]) -> str:
    """Convert MR diff list into readable text for AI prompt.

    Each diff line is prefixed with its actual file line number [N]
    so the AI can reference correct line positions.
    """
    if not diff:
        return ""

    parts = []
    for item in diff:
        file_path = item.get("new_path", item.get("old_path", "unknown"))
        diff_content = item.get("diff", "")

        if item.get("new_file"):
            parts.append(f"--- NEW FILE: {file_path} ---\n{_add_line_numbers(diff_content, new_only=True)}")
        elif item.get("deleted_file"):
            parts.append(f"--- DELETED FILE: {file_path} ---")
        elif item.get("renamed_file"):
            old = item.get("old_path", "")
            parts.append(f"--- RENAMED: {old} -> {file_path} ---\n{_add_line_numbers(diff_content)}")
        else:
            parts.append(f"--- {file_path} ---\n{_add_line_numbers(diff_content)}")

    return "\n\n".join(parts)


def _add_line_numbers(diff_content: str, new_only: bool = False) -> str:
    """Prefix each diff line with its file line number [N].

    - Context lines: show the actual file line number
    - '-' lines: show the old file line number
    - '+' lines: show the new file line number
    - '@@' headers: keep as-is (AI can see the starting line)
    """
    lines = diff_content.split("\n")
    old_line = 0
    new_line = 0

    # Initialize from first hunk header
    for line in lines:
        m = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if m:
            old_line = int(m.group(1))
            new_line = int(m.group(2))
            break

    result = []
    for line in lines:
        m = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if m:
            old_line = int(m.group(1))
            new_line = int(m.group(2))
            result.append(line)
        elif line.startswith("-"):
            result.append(f"[{old_line}]{line}")
            old_line += 1
        elif line.startswith("+"):
            result.append(f"[{new_line}]{line}")
            new_line += 1
        elif line.startswith("\\"):
            result.append(line)
        else:
            if line:
                result.append(f"[{new_line}]{line}")
            old_line += 1
            new_line += 1

    return "\n".join(result)


def build_line_mapping(diff: list[dict]) -> tuple[dict[str, dict[int, int | None]], dict[str, set[int]]]:
    """Build new_line -> old_line mapping for each changed file.

    Returns (mapping, modified_lines)
    - mapping: {file_path: {new_line: old_line_or_none}}
      - old_line is None for new-only lines
      - old_line is int for context lines (old and new both exist)
      - old_line is int for modified lines (preceded by a '-')
    - modified_lines: {file_path: set of new_line numbers that are modifications}

    GitLab requires different line_code handling:
    - Context lines: old_line (int) + line_code(sha1 with old_line) works
    - Modified lines: old_line='' (empty str) + line_code works
    - Pure additions: no old_line, no line_code works
    """
    mapping: dict[str, dict[int, int | None]] = {}
    modified: dict[str, set[int]] = {}

    for item in diff:
        file_path = item.get("new_path")
        diff_content = item.get("diff", "")
        if not file_path or not diff_content:
            continue

        lines = diff_content.split("\n")
        old_line = 0
        new_line = 0
        had_deletion = False

        for line in lines:
            m = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if m:
                old_line = int(m.group(1))
                new_line = int(m.group(2))
                had_deletion = False
                continue

            if line.startswith("-"):
                had_deletion = True
                old_line += 1
            elif line.startswith("+"):
                if had_deletion:
                    modified.setdefault(file_path, set()).add(new_line)
                    mapping.setdefault(file_path, {})[new_line] = old_line - 1
                    had_deletion = False
                else:
                    mapping.setdefault(file_path, {})[new_line] = None
                new_line += 1
            else:
                if line:
                    mapping.setdefault(file_path, {})[new_line] = old_line
                had_deletion = False
                old_line += 1
                new_line += 1

    return mapping, modified

## Review Rules: Info (Maintainability Suggestions)

This file defines maintainability-suggestion-level review rules. When info issues are found, the Score is in the **80-100** range and the Status is **Pass**.

### Review Attitude

- **Report only obvious, non-controversial maintainability issues.**
- **Do not report code style preferences** (indentation, quotes, naming conventions, etc. — subjective issues); those are handled by linters.
- **Do not report formatting issues** (blank lines, spaces, line breaks, etc.); those are handled by formatters.
- **Do not report test coverage** — the AI can only see the diff and cannot judge coverage.

---

### 1. Dead Code

The following issues add cognitive load without any value:

- **Unused imports**: Modules or functions imported but never used in the current file.
- **Commented-out code blocks**: Code that is commented out but not deleted. Git preserves history; comments are not needed to keep it.
- **Functions/methods that will never be called**: Functions defined but not called anywhere (excluding public APIs and callbacks).

### 2. Naming & Expression

The following issues reduce code readability:

- **Names that fail to express intent**: Using names like `data`, `temp`, `flag`, `process` that don't convey specific meaning.
- **Boolean variables not phrased as questions**: Boolean variables should use prefixes like `is_`, `has_`, `should_`, `can_`. `enabled` is less clear than `is_enabled`.
- **Meaningless abbreviations**: Abbreviations like `btn`, `mgr`, `util`, `helper`, `ctx`, `req`, `res` reduce readability (unless the project has a clear abbreviation convention).

### 3. Duplication & Magic Values

The following issues increase maintenance cost:

- **Same logic appearing three or more times**: Identical or highly similar code appearing 3+ times should be extracted into a function/module.
- **Hardcoded numeric/string constants**: Numbers (e.g. `timeout = 30`, `status == 2`) or strings (e.g. paths, URLs, key names) appearing directly in code should be extracted into named constants. Exception: conventional values like 0, 1, -1 do not need constants.

### 4. Missing Documentation

The following issues make code hard to understand and maintain:

- **Public APIs missing parameter docs**: Functions/methods exposed by a module lack documentation of parameter types, meanings, and return values.
- **Complex algorithms missing explanations**: Non-obvious algorithmic logic lacks comments explaining the approach and rationale.
- **Non-obvious business logic missing comments**: Code's "why" (business reasons) rather than "what" needs comment coverage.

---

### Scoring Guide

| Findings | Score | Status |
|----------|-------|--------|
| Info issues only | 80-100 | Pass |
| No issues at all | 90-100 | Pass |
| Any warning or critical issue | See corresponding file | See corresponding file |

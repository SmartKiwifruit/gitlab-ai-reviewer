# GitLab AI Reviewer

[![CI](https://github.com/SmartKiwifruit/gitlab-ai-reviewer/actions/workflows/ci.yml/badge.svg)](https://github.com/SmartKiwifruit/gitlab-ai-reviewer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Automated AI-powered code review for GitLab Merge Requests.

[中文文档](README.zh-CN.md)

## Features

- **Webhook-driven** — triggers a review automatically when a merge request is opened or reopened
- **Multi-provider AI** — supports Claude, OpenAI-compatible APIs, and Qwen (DashScope), with a custom base URL for internal proxies
- **Customizable review rules ("skills")** — drop Markdown rule files into `.ai-review/skills/` on your target branch and the reviewer will follow them; sensible defaults are built in
- **Structured output** — score (0–100), Pass / Needs Revision verdict, and per-line comments with severity levels (critical / warning / info)
- **Inline comments** — review findings are posted as inline diff comments on the MR Changes tab, grouped per line
- **Review labels** — automatically applies `AI-Review: Passed`, `AI-Review: Needs Revision`, `AI-Review: Skill Changed`, `AI-Review: Needs Human Review`
- **Auto-merge** — automatically merges the MR when the review passes with zero findings
- **Manual override** — add the `AI-Review: Manual Override` label to skip AI review on any MR
- **Fast feedback** — posts a placeholder comment immediately, then updates it in place with the final report

## Architecture

```
GitLab (MR webhook)
   │
   ▼
FastAPI service (src/main.py)
   │  POST /webhook
   ▼
WebhookHandler (src/webhook/handler.py)
   ├── GitLabClient   ── fetch MR info, diff, file contents (src/gitlab/)
   ├── SkillsLoader   ── load review rules from .ai-review/skills/ or defaults (src/skills/)
   ├── AIClient       ── call the configured LLM provider (src/ai/)
   └── comments       ── post report, inline comments, labels (src/gitlab/comments.py)
```

## Quick Start

### Run with Docker (recommended)

```bash
cp .env.example .env   # fill in your GitLab and AI credentials
docker compose up -d
```

The service listens on port `8000`.

### Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:create_app --host 0.0.0.0 --port 8000 --factory
```

### Configure the GitLab webhook

In your GitLab project: **Settings → Webhooks**, then set:

- **URL**: `http://<your-host>:8000/webhook`
- **Trigger**: check `Merge request events`
- **Secret token**: (optional) the same value as `WEBHOOK_SECRET_TOKEN`

## Configuration

Environment variables (see [.env.example](.env.example)):

| Variable | Description |
|---|---|
| `GITLAB_URL` | GitLab instance base URL |
| `GITLAB_TOKEN` | GitLab personal access token with `api` scope |
| `AI_PROVIDER` | `claude` \| `openai` \| `qwen` |
| `AI_API_KEY` | API key for the chosen provider |
| `AI_MODEL` | Model name, e.g. `qwen3.6-plus` |
| `AI_BASE_URL` | Optional custom endpoint (internal proxy) |
| `WEBHOOK_SECRET_TOKEN` | Optional webhook secret |

Model defaults (max tokens, temperature) live in [config/settings.yaml](config/settings.yaml).

## Custom Review Rules (Skills)

Place Markdown files under `.ai-review/skills/` on the **target branch** of the reviewed project:

```
.ai-review/skills/
├── security.md      # e.g. security-focused rules
└── style.md
```

- Only the rules in these files are checked — the reviewer will not go beyond them.
- If the MR itself modifies `.ai-review/skills/`, the review is flagged for human attention (`AI-Review: Skill Changed`).
- With no custom skills, the built-in rules in [`default-skills/`](default-skills/) are used (critical / warning / info tiers).

## Review Output Format

The review posts a summary comment on the MR:

```
# AI Review Report
Score: 85/100
Status: ✅ Pass

### `src/app.py` line 42
1. Problem: SQL injection risk from string concatenation
   Suggestion: Use parameterized queries
```

Findings are also posted as inline comments on the exact diff lines.

## Development

```bash
pip install -r requirements.txt
pytest            # run the test suite (42 tests)
```

Project layout:

```
src/
├── main.py          # FastAPI app factory
├── ai/              # LLM client, prompt building, response parsing
├── gitlab/          # GitLab API client, diff processing, comment posting
├── skills/          # review rule loading (.ai-review/skills/ or defaults)
└── webhook/         # webhook event parsing and review orchestration
default-skills/      # built-in review rules (critical/warning/info)
tests/               # pytest test suite
```

## License

[MIT](LICENSE)

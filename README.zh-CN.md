# GitLab AI Reviewer

[![CI](https://github.com/SmartKiwifruit/gitlab-ai-reviewer/actions/workflows/ci.yml/badge.svg)](https://github.com/SmartKiwifruit/gitlab-ai-reviewer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 面向 GitLab Merge Request 的自动化 AI 代码审查服务。

[English](README.md)

## 功能特性

- **Webhook 驱动** —— MR 打开或重新打开时自动触发审查
- **多模型支持** —— 支持 Claude、OpenAI 兼容 API、通义千问（DashScope），可配置自定义代理地址
- **可定制审查规则（skills）** —— 在目标分支的 `.ai-review/skills/` 目录放入 Markdown 规则文件即可生效；内置默认规则开箱即用
- **结构化输出** —— 评分（0-100）、Pass / Needs Revision 结论，以及带严重级别（critical / warning / info）的逐行评论
- **行内评论** —— 审查结果以行内 diff 评论形式发布在 MR 的 Changes 页签，同一行的多个问题自动合并
- **审查标签** —— 自动打上 `AI-Review: Passed`、`AI-Review: Needs Revision`、`AI-Review: Skill Changed`、`AI-Review: Needs Human Review` 标签
- **自动合并** —— 审查通过且零问题时自动合并 MR
- **手动接管** —— 给 MR 加上 `AI-Review: Manual Override` 标签即可跳过 AI 审查
- **快速反馈** —— 立即发布占位评论，审查完成后原地更新为最终报告

## 架构

```
GitLab（MR webhook）
   │
   ▼
FastAPI 服务 (src/main.py)
   │  POST /webhook
   ▼
WebhookHandler (src/webhook/handler.py)
   ├── GitLabClient   ── 获取 MR 信息、diff、文件内容 (src/gitlab/)
   ├── SkillsLoader   ── 加载 .ai-review/skills/ 或默认审查规则 (src/skills/)
   ├── AIClient       ── 调用配置的大模型 (src/ai/)
   └── comments       ── 发布报告、行内评论、标签 (src/gitlab/comments.py)
```

## 快速开始

### Docker 运行（推荐）

```bash
cp .env.example .env   # 填入你的 GitLab 和 AI 凭据
docker compose up -d
```

服务监听 `8000` 端口。

### 本地运行

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:create_app --host 0.0.0.0 --port 8000 --factory
```

### 配置 GitLab Webhook

在 GitLab 项目中进入 **Settings → Webhooks**，配置：

- **URL**：`http://<你的主机>:8000/webhook`
- **Trigger**：勾选 `Merge request events`
- **Secret token**：（可选）与 `WEBHOOK_SECRET_TOKEN` 保持一致

## 配置说明

环境变量（见 [.env.example](.env.example)）：

| 变量 | 说明 |
|---|---|
| `GITLAB_URL` | GitLab 实例地址 |
| `GITLAB_TOKEN` | 具有 `api` 权限的 GitLab Personal Access Token |
| `AI_PROVIDER` | `claude` \| `openai` \| `qwen` |
| `AI_API_KEY` | 所选模型服务商的 API Key |
| `AI_MODEL` | 模型名称，如 `qwen3.6-plus` |
| `AI_BASE_URL` | 可选，自定义代理地址 |
| `WEBHOOK_SECRET_TOKEN` | 可选，webhook 密钥 |

模型默认参数（max tokens、temperature）在 [config/settings.yaml](config/settings.yaml) 中配置。

## 自定义审查规则（Skills）

在被审查项目的**目标分支**上放置 Markdown 文件：

```
.ai-review/skills/
├── security.md      # 例如：安全专项规则
└── style.md
```

- AI **只**按这些规则检查，不会扩展到规则之外。
- 如果 MR 本身修改了 `.ai-review/skills/`，审查会标记为需人工确认（`AI-Review: Skill Changed`）。
- 未配置自定义规则时，使用内置的 [`default-skills/`](default-skills/) 规则（critical / warning / info 三级）。

## 审查输出示例

审查结果会以汇总评论发布在 MR 上：

```
# AI Review Report
Score: 85/100
Status: ✅ Pass

### `src/app.py` line 42
1. Problem: SQL injection risk from string concatenation
   Suggestion: Use parameterized queries
```

同时会在对应 diff 行上发布行内评论。

## 开发

```bash
pip install -r requirements.txt
pytest            # 运行测试（42 个用例）
```

项目结构：

```
src/
├── main.py          # FastAPI 应用工厂
├── ai/              # 大模型客户端、提示词构建、响应解析
├── gitlab/          # GitLab API 客户端、diff 处理、评论发布
├── skills/          # 审查规则加载（.ai-review/skills/ 或默认规则）
└── webhook/         # webhook 事件解析与审查编排
default-skills/      # 内置审查规则（critical/warning/info）
tests/               # pytest 测试
```

## 协议

[MIT](LICENSE)

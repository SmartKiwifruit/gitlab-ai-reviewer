import asyncio
import logging
import os

from dotenv import load_dotenv
import yaml
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse

load_dotenv()

from src.gitlab.client import GitLabClient
from src.ai.client import AIClient
from src.skills.loader import SkillsLoader
from src.webhook.handler import WebhookHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_settings() -> dict:
    """Load settings from YAML file and environment variables."""
    settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
    with open(settings_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def _process_webhook(handler: WebhookHandler, payload: dict):
    """Run webhook processing in background (blocking HTTP calls run in thread)."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: handler.handle_sync(payload))


def create_app(
    gitlab_client=None,
    ai_client=None,
    skills_loader=None,
) -> FastAPI:
    if gitlab_client is None:
        settings = load_settings()
        gitlab_client = GitLabClient(
            url=os.getenv("GITLAB_URL", settings["gitlab"]["url"]),
            token=os.getenv("GITLAB_TOKEN"),
        )
        ai_client = AIClient(
            provider=os.getenv("AI_PROVIDER", settings["ai"]["provider"]),
            api_key=os.getenv("AI_API_KEY"),
            model=os.getenv("AI_MODEL", settings["ai"]["model"]),
            max_tokens=settings["ai"].get("max_tokens", 4000),
            temperature=settings["ai"].get("temperature", 0.1),
            base_url=os.getenv("AI_BASE_URL"),
        )
        skills_loader = SkillsLoader(
            gitlab=gitlab_client,
            project_id=0,
            target_branch="",
            default_skills_dir=os.path.join(os.path.dirname(__file__), "..", "default-skills"),
        )

    handler = WebhookHandler(
        gitlab=gitlab_client,
        ai_client=ai_client,
        skills_loader=skills_loader,
    )

    app = FastAPI(title="GitLab AI Reviewer")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/webhook")
    async def webhook(request: Request, background_tasks: BackgroundTasks):
        payload = await request.json()
        logger.info(f"Received webhook event: {payload.get('object_kind', 'unknown')}")

        background_tasks.add_task(_process_webhook, handler, payload)
        return JSONResponse(content={"status": "accepted"})

    return app


if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)

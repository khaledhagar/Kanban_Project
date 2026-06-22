import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException

from app.auth import current_user

# Load the project-root .env so OPENROUTER_API_KEY is available in local dev and
# tests. In Docker there is no .env file; the key is passed in as an env var, and
# load_dotenv does not override an already-set variable.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

router = APIRouter(prefix="/api")


class AIError(RuntimeError):
    """Raised when the AI call cannot be made (e.g. missing key)."""


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise AIError("OPENROUTER_API_KEY is not set")
    return key


def ask(prompt: str) -> str:
    """Send a single user prompt to the model and return the reply text."""
    response = httpx.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {_api_key()}"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


@router.get("/ai/health")
def ai_health(_: str = Depends(current_user)) -> dict[str, str]:
    """Diagnostic: confirm the backend can reach the model."""
    try:
        answer = ask("What is 2+2? Reply with only the number.")
    except AIError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"answer": answer}

import json
import os
import sqlite3
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError

from app import db
from app.auth import current_user
from app.board import Board, get_db

# Load the project-root .env so OPENROUTER_API_KEY is available in local dev and
# tests. In Docker there is no .env file; the key is passed in as an env var, and
# load_dotenv does not override an already-set variable.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

router = APIRouter(prefix="/api")


class AIError(RuntimeError):
    """Raised when the AI call cannot be made (e.g. missing key)."""


# Structured Outputs schema. The stored board keeps cards as a map keyed by id
# (Record<string, Card>), but strict Structured Outputs cannot express dynamic
# keys, so the AI exchanges cards as an array and we convert to/from the map.
_CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "details": {"type": "string"},
    },
    "required": ["id", "title", "details"],
    "additionalProperties": False,
}
_COLUMN_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "cardIds": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "title", "cardIds"],
    "additionalProperties": False,
}
_AI_BOARD_SCHEMA = {
    "type": "object",
    "properties": {
        "columns": {"type": "array", "items": _COLUMN_SCHEMA},
        "cards": {"type": "array", "items": _CARD_SCHEMA},
    },
    "required": ["columns", "cards"],
    "additionalProperties": False,
}
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        # null when the turn does not change the board.
        "board_update": {"anyOf": [_AI_BOARD_SCHEMA, {"type": "null"}]},
    },
    "required": ["reply", "board_update"],
    "additionalProperties": False,
}
_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "kanban_reply",
        "strict": True,
        "schema": _RESPONSE_SCHEMA,
    },
}


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise AIError("OPENROUTER_API_KEY is not set")
    return key


def _post(messages: list[dict], response_format: dict | None = None) -> str:
    """POST a chat completion and return the assistant message content."""
    body: dict = {"model": MODEL, "messages": messages}
    if response_format is not None:
        body["response_format"] = response_format
    response = httpx.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {_api_key()}"},
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def ask(prompt: str) -> str:
    """Send a single user prompt to the model and return the reply text."""
    return _post([{"role": "user", "content": prompt}])


def _board_to_ai(board: dict) -> dict:
    """Storage board (cards as a map) -> AI board (cards as a list)."""
    return {"columns": board["columns"], "cards": list(board["cards"].values())}


def _board_from_ai(ai_board: dict) -> dict:
    """AI board (cards as a list) -> storage board (cards as a map)."""
    return {
        "columns": ai_board["columns"],
        "cards": {card["id"]: card for card in ai_board["cards"]},
    }


def build_messages(board: dict, history: list[dict], message: str) -> list[dict]:
    """Assemble the request: system context + board JSON + history + question."""
    system = (
        "You are a project management assistant for a single Kanban board. "
        "Use the board below to answer questions, and when the user asks to "
        "create, edit, move, or delete cards or columns, return a board_update "
        "with the COMPLETE updated board (every column and card), not a diff. "
        "Keep existing ids stable and invent ids like 'card-xyz' for new cards. "
        "Each column's cardIds must reference cards present in the cards array. "
        "If the turn needs no board change, set board_update to null.\n\n"
        f"Board: {json.dumps(_board_to_ai(board))}"
    )
    return [
        {"role": "system", "content": system},
        *history,
        {"role": "user", "content": message},
    ]


def _validated_update(ai_board: dict) -> dict | None:
    """Convert and validate an AI board_update to the storage shape, or None.

    Rejecting (returning None) keeps a malformed update from corrupting the
    stored board; the reply still reaches the user.
    """
    try:
        storage = _board_from_ai(ai_board)
        return Board.model_validate(storage).model_dump()
    except (ValidationError, KeyError, TypeError):
        return None


def chat(board: dict, history: list[dict], message: str) -> dict:
    """Run one AI turn. Returns {reply, board_update} (update in storage shape)."""
    content = _post(build_messages(board, history, message), _RESPONSE_FORMAT)
    data = json.loads(content)
    update = data.get("board_update")
    return {
        "reply": data["reply"],
        "board_update": _validated_update(update) if update is not None else None,
    }


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


@router.get("/ai/health")
def ai_health(_: str = Depends(current_user)) -> dict[str, str]:
    """Diagnostic: confirm the backend can reach the model."""
    try:
        answer = ask("What is 2+2? Reply with only the number.")
    except AIError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"answer": answer}


@router.post("/ai/chat")
def ai_chat(
    request: ChatRequest,
    username: str = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Chat over the user's board; apply and persist a board_update when present."""
    board = db.get_or_create_board(conn, username)
    history = [message.model_dump() for message in request.history]
    try:
        result = chat(board, history, request.message)
    except AIError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if result["board_update"] is not None:
        board = db.save_board(conn, username, result["board_update"])
    return {"reply": result["reply"], "board": board}

import json
import os
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import ai
from app.main import create_app

GOOD = {"username": "user", "password": "password"}

# Opt-in live tests: only run when a key is present AND explicitly enabled, so a
# normal `pytest` never makes a paid network call.
LIVE = os.environ.get("OPENROUTER_API_KEY") and os.environ.get("RUN_LIVE_AI")
live_only = pytest.mark.skipif(
    not LIVE, reason="set OPENROUTER_API_KEY and RUN_LIVE_AI to run live AI tests"
)


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


def test_ask_builds_request_and_parses_reply(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse(
            {"choices": [{"message": {"content": "4"}}]}
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai.httpx, "post", fake_post)

    assert ai.ask("What is 2+2?") == "4"
    assert captured["url"] == ai.OPENROUTER_URL
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == ai.MODEL
    assert captured["json"]["messages"] == [
        {"role": "user", "content": "What is 2+2?"}
    ]


def test_ask_without_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ai.AIError):
        ai.ask("hi")


def authed_client(tmp_path: Path) -> TestClient:
    client = TestClient(create_app(db_path=tmp_path / "pm.db"))
    client.post("/api/login", json=GOOD)
    return client


def test_ai_health_requires_auth(tmp_path: Path):
    client = TestClient(create_app(db_path=tmp_path / "pm.db"))
    assert client.get("/api/ai/health").status_code == 401


def test_ai_health_returns_answer(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(ai, "ask", lambda prompt: "4")
    client = authed_client(tmp_path)
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    assert response.json() == {"answer": "4"}


def test_ai_health_reports_missing_key(tmp_path: Path, monkeypatch):
    def boom(prompt):
        raise ai.AIError("OPENROUTER_API_KEY is not set")

    monkeypatch.setattr(ai, "ask", boom)
    client = authed_client(tmp_path)
    response = client.get("/api/ai/health")
    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


# --- Part 9: structured chat over the board ---

# Minimal storage-shape board (cards as a map) and an AI-shape update (cards as
# a list, as the model returns them).
STORAGE_BOARD = {
    "columns": [{"id": "col-1", "title": "Todo", "cardIds": []}],
    "cards": {},
}
SAMPLE_UPDATE = {
    "columns": [{"id": "col-1", "title": "Todo", "cardIds": ["card-9"]}],
    "cards": [{"id": "card-9", "title": "New", "details": "From AI"}],
}


def chat_http(reply, board_update) -> FakeResponse:
    content = json.dumps({"reply": reply, "board_update": board_update})
    return FakeResponse({"choices": [{"message": {"content": content}}]})


def test_build_messages_includes_board_history_question():
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    messages = ai.build_messages(STORAGE_BOARD, history, "add a card")

    assert messages[0]["role"] == "system"
    assert "Board:" in messages[0]["content"]
    assert "col-1" in messages[0]["content"]  # board JSON is embedded
    assert messages[1:3] == history  # history preserved in order
    assert messages[-1] == {"role": "user", "content": "add a card"}


def test_chat_parses_reply_and_update(monkeypatch):
    monkeypatch.setattr(
        ai, "_post", lambda *a, **k: json.dumps(
            {"reply": "Added it", "board_update": SAMPLE_UPDATE}
        )
    )
    result = ai.chat(STORAGE_BOARD, [], "add a card")

    assert result["reply"] == "Added it"
    # cards come back as a map keyed by id in storage shape.
    assert result["board_update"]["cards"]["card-9"]["title"] == "New"
    assert result["board_update"]["columns"][0]["cardIds"] == ["card-9"]


def test_chat_reply_only_leaves_update_none(monkeypatch):
    monkeypatch.setattr(
        ai, "_post", lambda *a, **k: json.dumps(
            {"reply": "You have no cards", "board_update": None}
        )
    )
    result = ai.chat(STORAGE_BOARD, [], "how many cards?")

    assert result["reply"] == "You have no cards"
    assert result["board_update"] is None


def test_chat_rejects_malformed_update(monkeypatch):
    # Card missing title/details: fails Board validation, so it is dropped.
    bad = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": []}],
        "cards": [{"id": "card-9"}],
    }
    monkeypatch.setattr(
        ai, "_post", lambda *a, **k: json.dumps(
            {"reply": "tried", "board_update": bad}
        )
    )
    result = ai.chat(STORAGE_BOARD, [], "break it")

    assert result["reply"] == "tried"
    assert result["board_update"] is None


def test_ai_chat_requires_auth(tmp_path: Path):
    client = TestClient(create_app(db_path=tmp_path / "pm.db"))
    assert client.post("/api/ai/chat", json={"message": "hi"}).status_code == 401


def test_ai_chat_applies_and_persists_update(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "pm.db"
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["body"] = json
        return chat_http("Added a card", SAMPLE_UPDATE)

    monkeypatch.setattr(ai.httpx, "post", fake_post)

    client = TestClient(create_app(db_path=db_path))
    client.post("/api/login", json=GOOD)
    response = client.post("/api/ai/chat", json={"message": "add a card"})

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Added a card"
    assert body["board"]["cards"]["card-9"]["title"] == "New"
    # Strict Structured Outputs were requested.
    assert captured["body"]["response_format"]["json_schema"]["strict"] is True

    # The AI's update persisted: a fresh app over the same file sees it.
    restarted = TestClient(create_app(db_path=db_path))
    restarted.post("/api/login", json=GOOD)
    assert "card-9" in restarted.get("/api/board").json()["cards"]


def test_ai_chat_reports_missing_key(tmp_path: Path, monkeypatch):
    # No key: chat fails before any HTTP call, surfacing a clear 503.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = authed_client(tmp_path)
    response = client.post("/api/ai/chat", json={"message": "hi"})
    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_ai_chat_reply_only_leaves_board_unchanged(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        ai.httpx,
        "post",
        lambda url, headers, json, timeout: chat_http("You have 8 cards", None),
    )
    client = authed_client(tmp_path)
    before = client.get("/api/board").json()

    response = client.post("/api/ai/chat", json={"message": "how many cards?"})
    assert response.status_code == 200
    assert response.json()["reply"] == "You have 8 cards"
    assert client.get("/api/board").json() == before


@live_only
def test_live_two_plus_two():
    assert "4" in ai.ask("What is 2+2? Reply with only the number.")


@live_only
def test_live_chat_updates_board():
    """Smoke test: the live API accepts the strict chat schema and updates."""
    result = ai.chat(
        STORAGE_BOARD,
        [],
        "Add a card titled 'Buy milk' to the Todo column.",
    )
    assert isinstance(result["reply"], str) and result["reply"]
    update = result["board_update"]
    assert update is not None  # validated to storage shape
    titles = [card["title"].lower() for card in update["cards"].values()]
    assert any("milk" in title for title in titles)


@live_only
def test_live_structured_outputs():
    """Probe whether the model honors strict Structured Outputs on OpenRouter.

    Records the de-risking result for Part 9: a strict json_schema request should
    come back as JSON matching the schema.
    """
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "integer"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    response = httpx.post(
        ai.OPENROUTER_URL,
        headers={"Authorization": f"Bearer {ai._api_key()}"},
        json={
            "model": ai.MODEL,
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "answer",
                    "strict": True,
                    "schema": schema,
                },
            },
        },
        timeout=30,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)  # must be valid JSON per the schema
    assert parsed["answer"] == 4

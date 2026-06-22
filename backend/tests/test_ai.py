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


@live_only
def test_live_two_plus_two():
    assert "4" in ai.ask("What is 2+2? Reply with only the number.")


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

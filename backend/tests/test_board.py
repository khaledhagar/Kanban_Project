from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

GOOD = {"username": "user", "password": "password"}


def authed_client(tmp_path: Path) -> TestClient:
    client = TestClient(create_app(db_path=tmp_path / "pm.db"))
    client.post("/api/login", json=GOOD)
    return client


def test_read_returns_seeded_board(tmp_path: Path):
    client = authed_client(tmp_path)
    response = client.get("/api/board")
    assert response.status_code == 200
    board = response.json()
    assert len(board["columns"]) == 5
    assert len(board["cards"]) == 8


def test_update_persists_and_round_trips(tmp_path: Path):
    client = authed_client(tmp_path)
    board = client.get("/api/board").json()
    board["columns"][0]["title"] = "Renamed"

    saved = client.put("/api/board", json=board)
    assert saved.status_code == 200
    assert saved.json()["columns"][0]["title"] == "Renamed"

    reread = client.get("/api/board").json()
    assert reread["columns"][0]["title"] == "Renamed"


def test_board_routes_require_auth(tmp_path: Path):
    client = TestClient(create_app(db_path=tmp_path / "pm.db"))
    assert client.get("/api/board").status_code == 401
    assert client.put("/api/board", json={"columns": [], "cards": {}}).status_code == 401


def test_board_persists_across_app_restart(tmp_path: Path):
    db_path = tmp_path / "pm.db"

    client = TestClient(create_app(db_path=db_path))
    client.post("/api/login", json=GOOD)
    board = client.get("/api/board").json()
    board["cards"]["card-1"]["title"] = "Survives restart"
    client.put("/api/board", json=board)

    assert db_path.exists()  # DB auto-created on demand

    # A fresh app instance over the same file sees the persisted board.
    restarted = TestClient(create_app(db_path=db_path))
    restarted.post("/api/login", json=GOOD)
    assert (
        restarted.get("/api/board").json()["cards"]["card-1"]["title"]
        == "Survives restart"
    )

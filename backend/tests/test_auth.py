from fastapi.testclient import TestClient

from app.main import create_app

GOOD = {"username": "user", "password": "password"}


def make_client() -> TestClient:
    return TestClient(create_app())


def test_login_success_sets_session_and_me_reflects_it():
    client = make_client()
    assert client.get("/api/me").status_code == 401

    response = client.post("/api/login", json=GOOD)
    assert response.status_code == 200
    assert response.json() == {"username": "user"}
    assert "pm_session" in response.cookies

    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json() == {"username": "user"}


def test_login_wrong_credentials_rejected():
    client = make_client()
    response = client.post(
        "/api/login", json={"username": "user", "password": "nope"}
    )
    assert response.status_code == 401
    assert client.get("/api/me").status_code == 401


def test_logout_clears_session():
    client = make_client()
    client.post("/api/login", json=GOOD)
    assert client.get("/api/me").status_code == 200

    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/me").status_code == 401

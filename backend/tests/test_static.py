from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_serves_hello_world_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Hello from the Project Management MVP" in response.text

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, create_app

client = TestClient(app)


def test_root_serves_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_serves_app_shell_and_next_asset(tmp_path: Path):
    # A faithful stand-in for the exported Next.js bundle: an index shell plus a
    # hashed asset under /_next/static, mirroring the real export's shape.
    (tmp_path / "_next" / "static").mkdir(parents=True)
    (tmp_path / "index.html").write_text(
        "<!doctype html><div id='app-root'>Kanban Studio</div>"
    )
    (tmp_path / "_next" / "static" / "app.js").write_text("console.log('ok')")

    test_client = TestClient(create_app(tmp_path))

    root = test_client.get("/")
    assert root.status_code == 200
    assert "app-root" in root.text

    asset = test_client.get("/_next/static/app.js")
    assert asset.status_code == 200
    assert "console.log" in asset.text

    # API still wins over the static catch-all, and unknown paths 404.
    assert test_client.get("/api/health").json() == {"status": "ok"}
    assert test_client.get("/missing").status_code == 404

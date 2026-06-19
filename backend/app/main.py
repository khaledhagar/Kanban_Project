from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(static_dir: Path = DEFAULT_STATIC_DIR) -> FastAPI:
    app = FastAPI(title="Project Management MVP")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Serve the static site last so /api routes take precedence over the
    # catch-all at /. In production this directory holds the exported Next.js
    # bundle (including /_next assets); locally it is a placeholder page.
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app


app = create_app()

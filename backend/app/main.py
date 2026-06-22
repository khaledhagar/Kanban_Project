import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.ai import router as ai_router
from app.auth import router as auth_router
from app.board import router as board_router

DEFAULT_STATIC_DIR = Path(
    os.environ.get("PM_STATIC_DIR", Path(__file__).resolve().parent.parent / "static")
)


def create_app(
    static_dir: Path = DEFAULT_STATIC_DIR, db_path: Path = db.DEFAULT_DB_PATH
) -> FastAPI:
    app = FastAPI(title="Project Management MVP")
    app.state.db_path = db_path
    db.init_db(db_path)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(board_router)
    app.include_router(ai_router)

    # Serve the static site last so /api routes take precedence over the
    # catch-all at /. In production this directory holds the exported Next.js
    # bundle (including /_next assets); locally it is a placeholder page.
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app


app = create_app()

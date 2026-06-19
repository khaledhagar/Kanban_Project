from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Project Management MVP")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Serve the static site last so /api routes take precedence. In later parts this
# directory holds the exported Next.js bundle; for now it is a placeholder page.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

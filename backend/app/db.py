import json
import os
import sqlite3
from pathlib import Path

from app.auth import USERNAME

DEFAULT_DB_PATH = Path(
    os.environ.get(
        "PM_DB_PATH", Path(__file__).resolve().parent.parent / "data" / "pm.db"
    )
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  username   TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS boards (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL UNIQUE REFERENCES users(id),
  data       TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# The board a user starts with, mirroring the frontend initialData
# (src/lib/kanban.ts) so the first sign-in matches the demo.
SEED_BOARD: dict = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
}


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Create the schema if missing and ensure the hardcoded user exists."""
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO users (username) VALUES (?)", (USERNAME,)
        )
        conn.commit()
    finally:
        conn.close()


def _user_id(conn: sqlite3.Connection, username: str) -> int:
    # The user row is ensured by init_db, and only the hardcoded user can
    # authenticate, so a lookup is enough here.
    row = conn.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    return row["id"]


def get_or_create_board(conn: sqlite3.Connection, username: str) -> dict:
    row = conn.execute(
        "SELECT b.data FROM boards b "
        "JOIN users u ON u.id = b.user_id WHERE u.username = ?",
        (username,),
    ).fetchone()
    if row is not None:
        return json.loads(row["data"])
    return save_board(conn, username, SEED_BOARD)


def save_board(conn: sqlite3.Connection, username: str, data: dict) -> dict:
    user_id = _user_id(conn, username)
    conn.execute(
        "INSERT INTO boards (user_id, data) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "data = excluded.data, updated_at = datetime('now')",
        (user_id, json.dumps(data)),
    )
    conn.commit()
    return data

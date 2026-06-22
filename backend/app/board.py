import sqlite3
from typing import Iterator

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app import db
from app.auth import current_user

router = APIRouter(prefix="/api")


class Card(BaseModel):
    id: str
    title: str
    details: str


class Column(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class Board(BaseModel):
    columns: list[Column]
    cards: dict[str, Card]


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


@router.get("/board")
def read_board(
    username: str = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return db.get_or_create_board(conn, username)


@router.put("/board")
def write_board(
    board: Board,
    username: str = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return db.save_board(conn, username, board.model_dump())

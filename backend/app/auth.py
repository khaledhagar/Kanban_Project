import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

# Hardcoded MVP credentials (the database supports multiple users later).
USERNAME = "user"
PASSWORD = "password"
COOKIE_NAME = "pm_session"

# In-memory session store (token -> username). Not persisted; fine for the MVP.
_sessions: dict[str, str] = {}

router = APIRouter(prefix="/api")


class Credentials(BaseModel):
    username: str
    password: str


def current_user(pm_session: str | None = Cookie(default=None)) -> str:
    """Resolve the signed-in user from the session cookie, or 401."""
    username = _sessions.get(pm_session) if pm_session else None
    if username is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username


@router.post("/login")
def login(credentials: Credentials, response: Response) -> dict[str, str]:
    if credentials.username != USERNAME or credentials.password != PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    _sessions[token] = credentials.username
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"username": credentials.username}


@router.post("/logout")
def logout(
    response: Response, pm_session: str | None = Cookie(default=None)
) -> dict[str, bool]:
    if pm_session:
        _sessions.pop(pm_session, None)
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(username: str = Depends(current_user)) -> dict[str, str]:
    return {"username": username}

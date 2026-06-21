"""
DeltaForge - authentication.

A small, dependency-free auth layer for the dashboard. It provides user
registration, login and a current-user lookup, backed by a JSON file store.

Design choices (deliberately stdlib only, no new dependencies):
  - Passwords are hashed with PBKDF2-HMAC-SHA256 and a per-user salt.
  - Sessions use a compact HMAC-signed token (base64url payload + signature),
    verified server-side with a persisted secret. No external JWT library.

Storage location is the backend directory by default, override with
DELTAFORGE_DATA_DIR. The signing secret comes from DELTAFORGE_AUTH_SECRET if set,
otherwise a random secret is generated once and persisted so tokens survive a
restart.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import uuid

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

_PBKDF2_ROUNDS = 200_000
_TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 days

_DATA_DIR = os.environ.get(
    "DELTAFORGE_DATA_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_USERS_PATH = os.path.join(_DATA_DIR, "users.json")
_SECRET_PATH = os.path.join(_DATA_DIR, ".auth_secret")


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _load_secret() -> bytes:
    env = os.environ.get("DELTAFORGE_AUTH_SECRET")
    if env:
        return env.encode("utf-8")
    try:
        with open(_SECRET_PATH, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        secret = secrets.token_bytes(32)
        try:
            with open(_SECRET_PATH, "wb") as fh:
                fh.write(secret)
            os.chmod(_SECRET_PATH, 0o600)
        except OSError:
            # Read-only filesystem: fall back to a process-lifetime secret.
            pass
        return secret


class UserStore:
    """Thread-safe JSON-file-backed user store."""

    def __init__(self, path: str = _USERS_PATH):
        self._path = path
        self._lock = threading.RLock()
        self._users: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self._path) as fh:
                data = json.load(fh)
            self._users = {u["email"].lower(): u for u in data.get("users", [])}
        except (FileNotFoundError, json.JSONDecodeError):
            self._users = {}

    def _save(self) -> None:
        tmp = f"{self._path}.tmp"
        with open(tmp, "w") as fh:
            json.dump({"users": list(self._users.values())}, fh, indent=2)
        os.replace(tmp, self._path)

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS
        )
        return dk.hex()

    def register(self, name: str, email: str, password: str) -> dict:
        email_key = email.strip().lower()
        if not email_key or "@" not in email_key:
            raise ValueError("A valid email is required.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        with self._lock:
            if email_key in self._users:
                raise KeyError("An account with that email already exists.")
            salt = secrets.token_bytes(16)
            user = {
                "id": uuid.uuid4().hex,
                "name": (name or "").strip() or email_key.split("@")[0],
                "email": email_key,
                "salt": salt.hex(),
                "password_hash": self._hash_password(password, salt),
                "created_at": time.time(),
            }
            self._users[email_key] = user
            self._save()
            return self._public(user)

    def verify(self, email: str, password: str) -> dict | None:
        with self._lock:
            user = self._users.get(email.strip().lower())
        if not user:
            return None
        salt = bytes.fromhex(user["salt"])
        candidate = self._hash_password(password, salt)
        if hmac.compare_digest(candidate, user["password_hash"]):
            return self._public(user)
        return None

    def by_id(self, user_id: str) -> dict | None:
        with self._lock:
            for user in self._users.values():
                if user["id"] == user_id:
                    return self._public(user)
        return None

    @staticmethod
    def _public(user: dict) -> dict:
        return {"id": user["id"], "name": user["name"], "email": user["email"]}


def create_token(user: dict, secret: bytes) -> str:
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "exp": int(time.time()) + _TOKEN_TTL_SECONDS,
    }
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _b64e(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_token(token: str, secret: bytes) -> dict | None:
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    expected = _b64e(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_b64d(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


# ── request / response models ─────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str = ""
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def build_auth_router(store: UserStore, secret: bytes) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    def _current_user(authorization: str | None) -> dict:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token.")
        token = authorization.split(" ", 1)[1].strip()
        payload = verify_token(token, secret)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        user = store.by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=401, detail="User no longer exists.")
        return user

    @router.post("/register")
    def register(req: RegisterRequest):
        try:
            user = store.register(req.name, req.email, req.password)
        except KeyError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"token": create_token(user, secret), "user": user}

    @router.post("/login")
    def login(req: LoginRequest):
        user = store.verify(req.email, req.password)
        if not user:
            raise HTTPException(status_code=401, detail="Incorrect email or password.")
        return {"token": create_token(user, secret), "user": user}

    @router.get("/me")
    def me(authorization: str | None = Header(default=None)):
        return {"user": _current_user(authorization)}

    return router

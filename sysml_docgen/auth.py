"""Small token-based authentication helper for the local prototype."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from typing import Any


SECRET = os.environ.get("SYSML_AUTH_SECRET", "sysml-docgen-course-design-secret")
TOKEN_TTL_SECONDS = int(os.environ.get("SYSML_TOKEN_TTL_SECONDS", str(8 * 60 * 60)))
USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,30}$")


def _legacy_hash(password: str) -> str:
    return hashlib.sha256(f"sysml-docgen:{password}".encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000).hex()
    return f"pbkdf2_sha256$120000${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, digest = stored_hash.split("$", 3)
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt),
                int(iterations),
            ).hex()
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(candidate, digest)
    return hmac.compare_digest(stored_hash, _legacy_hash(password))


DEMO_USERS = {
    "teacher": {"password_hash": _legacy_hash("teacher123"), "role": "user", "display": "Teacher"},
    "engineer": {"password_hash": _legacy_hash("engineer123"), "role": "user", "display": "Engineer"},
    "reviewer": {"password_hash": _legacy_hash("reviewer123"), "role": "user", "display": "Reviewer"},
}

DEMO_USER_SEEDS = {
    "teacher": {"password": "teacher123", "role": "user", "display": "Teacher"},
    "engineer": {"password": "engineer123", "role": "user", "display": "Engineer"},
    "reviewer": {"password": "reviewer123", "role": "user", "display": "Reviewer"},
}


VALID_ROLES = {"user"}


def _normalize_role(role: str | None) -> str:
    return "user"


def _normalize_username(username: str | None) -> str:
    return (username or "").strip()


def _validate_username(username: str) -> None:
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Username must be 3 to 30 letters, digits, underscores, or hyphens")


def _validate_password(password: str) -> None:
    if len(password) < 7:
        raise ValueError("Password must be at least 7 characters long")


def login(store: Any | None = None, username: str | None = None, password: str | None = None) -> dict[str, Any] | None:
    if password is None and isinstance(store, str) and isinstance(username, str):
        password = username
        username = store
        store = None
    if username is None or password is None:
        raise ValueError("Username and password are required")
    username = _normalize_username(username)
    user = get_user(store, username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    identity = {
        "username": username,
        "role": user["role"],
        "display": user["display"],
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    identity["token"] = issue_token(identity)
    return identity


def register(
    store: Any,
    username: str,
    password: str,
    role: str = "user",
    display: str | None = None,
) -> dict[str, Any] | None:
    username = _normalize_username(username)
    normalized_role = _normalize_role(role)
    if normalized_role not in VALID_ROLES:
        raise ValueError("Invalid role")
    if not username or not password:
        raise ValueError("Username and password are required")
    _validate_username(username)
    _validate_password(password)
    if get_user(store, username) is not None:
        raise ValueError(f"Username '{username}' already exists")
    password_hash = hash_password(password)
    display = (display or username).strip() or username
    if not hasattr(store, "create_user"):
        raise RuntimeError("User registration is not supported by the current store")
    store.create_user(username, password_hash, normalized_role, display)
    identity = {
        "username": username,
        "role": normalized_role,
        "display": display,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    identity["token"] = issue_token(identity)
    return identity


def get_user(store: Any, username: str) -> dict[str, Any] | None:
    if hasattr(store, "get_user"):
        return store.get_user(username)
    return DEMO_USERS.get(username)


def issue_token(identity: dict[str, Any]) -> str:
    payload = {
        "username": identity["username"],
        "role": identity["role"],
        "display": identity.get("display", identity["username"]),
        "exp": identity["exp"],
    }
    raw_payload = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
    signature = hmac.new(SECRET.encode("utf-8"), raw_payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{raw_payload}.{signature}"


def verify_token(token: str) -> dict[str, Any] | None:
    if "." not in token:
        return None
    raw_payload, signature = token.rsplit(".", 1)
    expected = hmac.new(SECRET.encode("utf-8"), raw_payload.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(raw_payload.encode("ascii")).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def identity_from_headers(headers: Any) -> dict[str, str]:
    authorization = headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        identity = verify_token(authorization.removeprefix("Bearer ").strip())
        if identity:
            return {
                "username": str(identity["username"]),
                "role": str(identity["role"]),
                "display": str(identity.get("display", identity["username"])),
            }
    username = headers.get("X-User", "engineer")
    role = headers.get("X-Role", "user")
    return {"username": username, "role": role, "display": username}

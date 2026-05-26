"""In-memory password reset flow for the local prototype."""

from __future__ import annotations

import random
import string
import time
from typing import Any


RESET_REQUESTS: dict[str, dict[str, Any]] = {}
RESET_TTL_SECONDS = 10 * 60


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _generate_code() -> str:
    return "".join(random.choice(string.digits) for _ in range(6))


def create_reset_request(store: Any, email: str) -> dict[str, Any]:
    username = email.strip()
    user = get_user(store, username)
    if user is None:
        user = next((item for item in iter_users(store) if item.get("display", "").lower() == _normalize_email(email)), None)
    if user is None:
        raise ValueError("Account not found")

    code = _generate_code()
    request_id = f"reset-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
    RESET_REQUESTS[request_id] = {
        "id": request_id,
        "username": user["username"],
        "email": email,
        "code": code,
        "expires_at": time.time() + RESET_TTL_SECONDS,
        "verified": False,
    }
    return {
        "request_id": request_id,
        "delivery": "local-demo",
        "code": code,
        "expires_at": RESET_REQUESTS[request_id]["expires_at"],
    }


def verify_reset_code(request_id: str, code: str) -> dict[str, Any]:
    request = RESET_REQUESTS.get(request_id)
    if request is None:
        raise ValueError("Reset request not found")
    if request["expires_at"] < time.time():
        RESET_REQUESTS.pop(request_id, None)
        raise ValueError("Reset code expired")
    if request["code"] != code.strip():
        raise ValueError("Invalid reset code")
    request["verified"] = True
    return {"request_id": request_id, "username": request["username"], "verified": True}


def set_new_password(store: Any, request_id: str, new_password: str) -> dict[str, Any]:
    from .auth import hash_password

    request = RESET_REQUESTS.get(request_id)
    if request is None:
        raise ValueError("Reset request not found")
    if not request.get("verified"):
        raise ValueError("Reset code not verified")
    user = get_user(store, request["username"])
    if user is None:
        raise ValueError("Account not found")
    if not hasattr(store, "create_user"):
        raise RuntimeError("Password reset is not supported by the current store")
    update_user_password(store, request["username"], hash_password(new_password), user["role"], user["display"])
    RESET_REQUESTS.pop(request_id, None)
    return {"username": request["username"], "reset": True}


def get_user(store: Any, username: str) -> dict[str, Any] | None:
    if hasattr(store, "get_user"):
        return store.get_user(username)
    return None


def iter_users(store: Any) -> list[dict[str, Any]]:
    if hasattr(store, "list_users"):
        return store.list_users()
    return []


def update_user_password(store: Any, username: str, password_hash: str, role: str, display: str) -> None:
    if hasattr(store, "upsert_user"):
        store.upsert_user(username, password_hash, role, display)
        return
    raise RuntimeError("Password reset is not supported by the current store")


def clear_reset_requests() -> None:
    RESET_REQUESTS.clear()

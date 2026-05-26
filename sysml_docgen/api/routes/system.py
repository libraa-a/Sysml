"""Routes for health, ops, and authentication."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from ..deps import get_store, read_identity
from ...store import ConflictError
from ...password_reset import create_reset_request, set_new_password, verify_reset_code
from ...services.system_service import SystemService


router = APIRouter()


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=30)
    password: str = Field(min_length=1, max_length=128)


class RegisterPayload(LoginPayload):
    role: str = "user"
    display: str | None = None


class ForgotPasswordPayload(BaseModel):
    email: str = Field(min_length=1, max_length=128)


class ResetVerifyPayload(BaseModel):
    request_id: str = Field(min_length=1)
    code: str = Field(min_length=6, max_length=6)


class ResetPasswordPayload(BaseModel):
    request_id: str = Field(min_length=1)
    password: str = Field(min_length=7, max_length=128)


def get_system_service(store: Any = Depends(get_store)) -> SystemService:
    return SystemService(store)


@router.get("/api/health", tags=["MMS"])
async def health(
    request: Request,
    identity: dict[str, str] = Depends(read_identity),
    service: SystemService = Depends(get_system_service),
) -> dict[str, Any]:
    return service.health_payload(identity, request.app.state.frontend_dir, request.app.state.frontend_mode)


@router.get("/api/ready", tags=["Ops"])
async def ready(
    request: Request,
    service: SystemService = Depends(get_system_service),
) -> dict[str, Any]:
    return service.ready_payload(request.app.state.frontend_dir, request.app.state.frontend_mode)


@router.get("/api/metrics", tags=["Ops"])
async def metrics(service: SystemService = Depends(get_system_service)) -> Response:
    return Response(service.metrics_text(), media_type="text/plain; version=0.0.4")


@router.post("/api/auth/login", tags=["MMS"])
async def auth_login(payload: LoginPayload, service: SystemService = Depends(get_system_service)) -> dict[str, Any]:
    identity = service.login(payload.username, payload.password)
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"identity": identity}


@router.get("/api/auth/me", tags=["MMS"])
async def auth_me(identity: dict[str, str] = Depends(read_identity)) -> dict[str, Any]:
    return {"identity": identity}


@router.post("/api/auth/register", tags=["MMS"])
async def auth_register(payload: RegisterPayload, service: SystemService = Depends(get_system_service)) -> dict[str, Any]:
    try:
        identity = service.register(
            payload.username,
            payload.password,
            payload.role,
            payload.display,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not identity:
        raise HTTPException(status_code=400, detail="Registration failed")
    return {"identity": identity}


@router.post("/api/auth/forgot-password", tags=["MMS"])
async def auth_forgot_password(payload: ForgotPasswordPayload, store: Any = Depends(get_store)) -> dict[str, Any]:
    try:
        return create_reset_request(store, payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/api/auth/reset-password/verify", tags=["MMS"])
async def auth_reset_verify(payload: ResetVerifyPayload) -> dict[str, Any]:
    try:
        return verify_reset_code(payload.request_id, payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/auth/reset-password", tags=["MMS"])
async def auth_reset_password(payload: ResetPasswordPayload, store: Any = Depends(get_store)) -> dict[str, Any]:
    try:
        return set_new_password(store, payload.request_id, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

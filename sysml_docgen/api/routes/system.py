"""Routes for health, ops, and authentication."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from ..deps import get_store, read_identity
from ...store import ConflictError
from ...services.system_service import SystemService


router = APIRouter()


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
async def auth_login(payload: dict[str, Any], service: SystemService = Depends(get_system_service)) -> dict[str, Any]:
    identity = service.login(payload.get("username", ""), payload.get("password", ""))
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"identity": identity}


@router.post("/api/auth/register", tags=["MMS"])
async def auth_register(payload: dict[str, Any], service: SystemService = Depends(get_system_service)) -> dict[str, Any]:
    try:
        identity = service.register(
            payload.get("username", ""),
            payload.get("password", ""),
            payload.get("role", "author"),
            payload.get("display"),
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

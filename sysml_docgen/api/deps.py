"""Shared FastAPI dependencies for auth and service access."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, Header, Request

from ..auth import identity_from_headers
from ..services.docgen_service import DocgenService
from ..services.ai_service import AiDocgenService
from ..services.integration_service import IntegrationService
from ..services.mms_service import MmsService
from ..repository import enforce_role


def get_store(request: Request) -> Any:
    return request.app.state.store


def get_mms_service(store: Any = Depends(get_store)) -> MmsService:
    return MmsService(store)


def get_docgen_service(store: Any = Depends(get_store)) -> DocgenService:
    return DocgenService(store)


def get_ai_docgen_service(store: Any = Depends(get_store)) -> AiDocgenService:
    return AiDocgenService(store)


def get_import_jobs(request: Request) -> dict[str, dict[str, Any]]:
    if not hasattr(request.app.state, "import_jobs"):
        request.app.state.import_jobs = {}
    return request.app.state.import_jobs


def get_integration_service(
    store: Any = Depends(get_store),
    import_jobs: dict[str, dict[str, Any]] = Depends(get_import_jobs),
) -> IntegrationService:
    return IntegrationService(store, import_jobs)


async def read_identity(
    request: Request,
    authorization: str | None = Header(default=None),
    x_user: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
) -> dict[str, str]:
    del request
    headers = {
        "Authorization": authorization or "",
        "X-User": x_user or "engineer",
        "X-Role": x_role or "user",
    }
    return identity_from_headers(headers)


async def authorize_read(request: Request, identity: dict[str, str] = Depends(read_identity)) -> dict[str, str]:
    enforce_role(request.method, identity["role"])
    return identity


async def authorize_write(request: Request, identity: dict[str, str] = Depends(read_identity)) -> dict[str, str]:
    enforce_role(request.method, identity["role"])
    return identity

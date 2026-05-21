"""Routes for MDK, XMI, and external tool integrations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from ..deps import authorize_read, authorize_write, get_docgen_service, get_integration_service
from ...services.docgen_service import DocgenService
from ...services.integration_service import IntegrationService


router = APIRouter()


@router.get("/api/mdk/adapters", tags=["MDK"])
async def mdk_adapters(
    _: dict[str, str] = Depends(authorize_read),
    service: IntegrationService = Depends(get_integration_service),
) -> dict[str, Any]:
    return {"adapters": service.list_adapters()}


@router.post("/api/mdk/parse", tags=["MDK"])
async def parse_sysml(
    payload: dict[str, Any],
    _: dict[str, str] = Depends(authorize_read),
    service: IntegrationService = Depends(get_integration_service),
) -> dict[str, Any]:
    return service.parse_sysml(payload)


@router.post("/api/mdk/import-jobs", tags=["MDK"])
async def create_mdk_import_job(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: IntegrationService = Depends(get_integration_service),
) -> dict[str, Any]:
    return service.create_import_job(payload, identity["username"])


@router.get("/api/mdk/import-jobs/{job_id}", tags=["MDK"])
async def get_mdk_import_job(
    job_id: str,
    _: dict[str, str] = Depends(authorize_read),
    service: IntegrationService = Depends(get_integration_service),
) -> dict[str, Any]:
    return service.get_import_job(job_id)


@router.post("/api/mdk/import-jobs/{job_id}/apply", tags=["MDK"])
async def apply_mdk_import_job(
    job_id: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: IntegrationService = Depends(get_integration_service),
) -> dict[str, Any]:
    return service.apply_import_job(job_id, payload, identity["username"])


@router.post("/api/mdk/push", tags=["MDK"])
async def mdk_push_model(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: IntegrationService = Depends(get_integration_service),
) -> dict[str, Any]:
    return service.push_model(payload, identity["username"])


@router.get("/api/mdk/pull", tags=["MDK"])
async def mdk_pull_model(
    project: str = "satellite-power",
    branch: str = "main",
    format: str = "json",
    _: dict[str, str] = Depends(authorize_read),
    service: IntegrationService = Depends(get_integration_service),
) -> Any:
    exported = service.pull_model(project, branch, format)
    if format.lower() == "xmi":
        return Response(exported, media_type="application/xml")
    return exported


@router.post("/api/mdk/generate", tags=["MDK", "DocGen"])
async def mdk_generate_doc(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    docgen_service: DocgenService = Depends(get_docgen_service),
) -> Any:
    doc_type = payload.get("doc_type") or payload.get("format") or "html"
    return docgen_service.render_generated_document(
        payload,
        identity["username"],
        doc_type,
        "mdk_generate_doc",
        touch_project=True,
    )

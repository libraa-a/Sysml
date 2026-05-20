"""Routes for model management and VE operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from ..deps import authorize_read, authorize_write, get_mms_service
from ...services.mms_service import MmsService


router = APIRouter()


@router.get("/api/metamodel", tags=["MMS"])
async def metamodel(_: dict[str, str] = Depends(authorize_read), service: MmsService = Depends(get_mms_service)) -> dict[str, Any]:
    return service.metamodel()


@router.get("/api/projects", tags=["MMS"])
async def list_projects(_: dict[str, str] = Depends(authorize_read), service: MmsService = Depends(get_mms_service)) -> dict[str, Any]:
    return {"projects": service.list_projects()}


@router.post("/api/projects", tags=["MMS"])
async def create_project(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"project": service.create_project(payload, identity["username"])}


@router.get("/api/projects/{project_id}", tags=["MMS"])
async def get_project(
    project_id: str,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"project": service.get_project_summary(project_id)}


@router.get("/api/projects/{project_id}/branches", tags=["MMS"])
async def list_branches(
    project_id: str,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"branches": service.list_branches(project_id)}


@router.post("/api/projects/{project_id}/branches", tags=["MMS"])
async def create_branch(
    project_id: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"branch": service.create_branch(project_id, payload, identity["username"])}


@router.post("/api/projects/{project_id}/branches/{target_branch}/merge", tags=["MMS"])
async def merge_branch(
    project_id: str,
    target_branch: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return service.merge_branch(project_id, target_branch, payload, identity["username"])


@router.get("/api/projects/{project_id}/branches/{branch}/elements", tags=["MMS"])
async def list_elements(
    project_id: str,
    branch: str,
    type: str | None = None,
    q: str | None = None,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"elements": service.list_elements(project_id, branch, type, q)}


@router.post("/api/projects/{project_id}/branches/{branch}/elements", tags=["MMS"])
async def create_element(
    project_id: str,
    branch: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"element": service.create_element(project_id, branch, payload, identity["username"])}


@router.get("/api/projects/{project_id}/branches/{branch}/elements/{element_id}", tags=["MMS"])
async def get_element(
    project_id: str,
    branch: str,
    element_id: str,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"element": service.get_element(project_id, branch, element_id)}


@router.put("/api/projects/{project_id}/branches/{branch}/elements/{element_id}", tags=["MMS"])
async def update_element(
    project_id: str,
    branch: str,
    element_id: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"element": service.update_element(project_id, branch, element_id, payload, identity["username"])}


@router.delete("/api/projects/{project_id}/branches/{branch}/elements/{element_id}", tags=["MMS"])
async def delete_element(
    project_id: str,
    branch: str,
    element_id: str,
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return service.delete_element(project_id, branch, element_id, identity["username"])


@router.post("/api/projects/{project_id}/branches/{branch}/commit", tags=["MMS"])
async def commit(
    project_id: str,
    branch: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"commit": service.commit(project_id, branch, payload.get("message", "淇濆瓨妯″瀷蹇収"), identity["username"])}


@router.get("/api/projects/{project_id}/commits", tags=["MMS"])
async def list_commits(
    project_id: str,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"commits": service.list_commits(project_id)}


@router.get("/api/projects/{project_id}/branches/{branch}/diff", tags=["MMS"])
async def diff(
    project_id: str,
    branch: str,
    from_ref: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return service.diff(project_id, branch, from_ref, to)


@router.post("/api/projects/{project_id}/branches/{branch}/rollback", tags=["MMS"])
async def rollback(
    project_id: str,
    branch: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return service.rollback(project_id, branch, payload.get("commit", ""), identity["username"])


@router.get("/api/projects/{project_id}/tags", tags=["MMS"])
async def list_tags(
    project_id: str,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"tags": service.list_tags(project_id)}


@router.post("/api/projects/{project_id}/tags", tags=["MMS"])
async def create_tag(
    project_id: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"tag": service.create_tag(project_id, payload, identity["username"])}


@router.get("/api/projects/{project_id}/audit", tags=["MMS"])
async def list_audit(
    project_id: str,
    limit: int = 80,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"events": service.list_audit(project_id, limit)}


@router.post("/api/projects/{project_id}/branches/{branch}/import", tags=["MDK"])
async def import_model(
    project_id: str,
    branch: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return service.import_model(project_id, branch, payload, identity["username"])


@router.get("/api/projects/{project_id}/branches/{branch}/export", tags=["MDK"])
async def export_model(
    project_id: str,
    branch: str,
    format: str = "json",
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> Any:
    exported = service.export_model(project_id, branch, format)
    if format.lower() == "xmi":
        return Response(exported, media_type="application/xml")
    return exported


@router.get("/api/projects/{project_id}/branches/{branch}/validate", tags=["MMS"])
async def validate_model(
    project_id: str,
    branch: str,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return service.validate_model(project_id, branch)


@router.post("/api/mms/projects", tags=["MMS"])
async def mms_create_project(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"project": service.create_project(payload, identity["username"])}


@router.get("/api/mms/models/{model_name}", tags=["MMS"])
async def mms_get_model(
    model_name: str,
    project: str = "satellite-power",
    branch: str = "main",
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"model": service.get_model(model_name, project, branch)}


@router.post("/api/mms/models", tags=["MMS"])
async def mms_create_model(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return service.create_model(payload, identity["username"])


@router.put("/api/mms/models/{model_name}", tags=["MMS"])
async def mms_update_model(
    model_name: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return service.update_model(model_name, payload, identity["username"])


@router.delete("/api/mms/models/{model_name}", tags=["MMS"])
async def mms_delete_model(
    model_name: str,
    project: str = "satellite-power",
    branch: str = "main",
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return service.delete_model(model_name, project, branch, identity["username"])


@router.post("/api/mms/branches", tags=["MMS"])
async def mms_create_branch(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"branch": service.create_mms_branch(payload, identity["username"])}


@router.get("/api/mms/branches", tags=["MMS"])
async def mms_get_branches(
    project: str = "satellite-power",
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"branches": service.list_mms_branches(project)}


@router.get("/api/projects/{project_id}/branches/{branch}/diagram", tags=["VE"])
async def diagram(
    project_id: str,
    branch: str,
    type: str = "requirements",
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"diagram": service.diagram(project_id, branch, type)}


@router.get("/api/projects/{project_id}/branches/{branch}/traceability", tags=["VE"])
async def traceability(
    project_id: str,
    branch: str,
    _: dict[str, str] = Depends(authorize_read),
    service: MmsService = Depends(get_mms_service),
) -> dict[str, Any]:
    return {"traceability": service.traceability(project_id, branch)}

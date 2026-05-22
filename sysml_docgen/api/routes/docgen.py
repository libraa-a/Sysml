"""Routes for document generation and output files."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..deps import authorize_read, authorize_write, get_ai_docgen_service, get_docgen_service
from ...files import delete_output_file, list_output_files, resolve_output_file
from ...services.ai_service import AiDocgenService
from ...services.docgen_service import DocgenService


router = APIRouter()


@router.get("/api/docgen/config", tags=["DocGen"])
async def docgen_config(service: DocgenService = Depends(get_docgen_service)) -> dict[str, Any]:
    return service.config_payload()


@router.get("/api/projects/{project_id}/branches/{branch}/documents", tags=["DocGen"])
async def list_documents(
    project_id: str,
    branch: str,
    _: dict[str, str] = Depends(authorize_read),
    service: DocgenService = Depends(get_docgen_service),
) -> dict[str, Any]:
    return {"documents": service.list_documents(project_id, branch)}


@router.post("/api/projects/{project_id}/branches/{branch}/documents", tags=["DocGen"])
async def create_document(
    project_id: str,
    branch: str,
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: DocgenService = Depends(get_docgen_service),
) -> dict[str, Any]:
    return {"document": service.create_document(project_id, branch, payload, identity["username"])}


@router.post("/api/projects/{project_id}/branches/{branch}/docgen/ai-draft", tags=["DocGen", "AI"])
async def ai_docgen_draft(
    project_id: str,
    branch: str,
    payload: dict[str, Any],
    _: dict[str, str] = Depends(authorize_write),
    service: AiDocgenService = Depends(get_ai_docgen_service),
) -> dict[str, Any]:
    return await service.draft_docgen_template(project_id, branch, payload)


@router.post("/api/projects/{project_id}/branches/{branch}/ve/ai-review", tags=["VE", "AI"])
async def ai_model_review(
    project_id: str,
    branch: str,
    payload: dict[str, Any],
    _: dict[str, str] = Depends(authorize_read),
    service: AiDocgenService = Depends(get_ai_docgen_service),
) -> dict[str, Any]:
    return await service.review_model(project_id, branch, payload)


@router.post("/api/projects/{project_id}/branches/{branch}/ai/chat", tags=["VE", "AI"])
async def ai_model_chat(
    project_id: str,
    branch: str,
    payload: dict[str, Any],
    _: dict[str, str] = Depends(authorize_read),
    service: AiDocgenService = Depends(get_ai_docgen_service),
) -> dict[str, Any]:
    return await service.chat_about_model(project_id, branch, payload)


@router.get("/api/projects/{project_id}/branches/{branch}/documents/{document_id}", tags=["DocGen"])
async def get_document(
    project_id: str,
    branch: str,
    document_id: str,
    format: str = "json",
    _: dict[str, str] = Depends(authorize_read),
    service: DocgenService = Depends(get_docgen_service),
) -> Any:
    return service.get_document_payload(project_id, branch, document_id, format)


@router.post("/api/docgen/docx", tags=["DocGen"])
async def generate_docx(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: DocgenService = Depends(get_docgen_service),
) -> Any:
    return service.render_generated_document(payload, identity["username"], "docx", "generate_docx")


@router.post("/api/docgen/html", tags=["DocGen"])
async def generate_html(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: DocgenService = Depends(get_docgen_service),
) -> Any:
    return service.render_generated_document(payload, identity["username"], "html", "generate_html")


@router.post("/api/docgen/pdf", tags=["DocGen"])
async def generate_pdf(
    payload: dict[str, Any],
    identity: dict[str, str] = Depends(authorize_write),
    service: DocgenService = Depends(get_docgen_service),
) -> Any:
    return service.render_generated_document(payload, identity["username"], "pdf", "generate_pdf")


@router.get("/api/files", tags=["Ops"])
async def files(_: dict[str, str] = Depends(authorize_read)) -> dict[str, Any]:
    return {"files": list_output_files()}


@router.get("/api/files/{filename}", tags=["Ops"])
async def download_file(filename: str, _: dict[str, str] = Depends(authorize_read)) -> FileResponse:
    try:
        return FileResponse(resolve_output_file(filename))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc


@router.delete("/api/files/{filename}", tags=["Ops"])
async def remove_file(filename: str, _: dict[str, str] = Depends(authorize_write)) -> dict[str, str]:
    try:
        delete_output_file(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    return {"deleted": filename}

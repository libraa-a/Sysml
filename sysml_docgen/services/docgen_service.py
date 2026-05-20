"""Document generation service operations."""

from __future__ import annotations

import base64
from typing import Any

from fastapi import HTTPException
from fastapi.responses import HTMLResponse, Response

from ..config import DEFAULT_FONT, DEFAULT_THEME, FONT_PRESETS, PDF_ENGINE, THEME_PRESETS
from ..docgen import generate_document, html_to_pdf_bytes, pandoc_available, quarto_available
from ..repository_contract import RepositoryStore


class DocgenService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store

    def config_payload(self) -> dict[str, Any]:
        return {
            "themes": {key: {"label": value["label"]} for key, value in THEME_PRESETS.items()},
            "fonts": {key: {"label": value["label"], "family": value["family"]} for key, value in FONT_PRESETS.items()},
            "defaults": {"theme": DEFAULT_THEME, "font": DEFAULT_FONT},
            "pandoc_available": pandoc_available(),
            "quarto_available": quarto_available(),
            "docx_available": True,
            "pdf_engine": PDF_ENGINE,
        }

    def list_documents(self, project_id: str, branch: str) -> list[dict[str, Any]]:
        return self.store.list_documents(project_id, branch)

    def create_document(self, project_id: str, branch: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        return self._generate_document(
            project_id,
            branch,
            payload.get("template"),
            payload.get("format", "html"),
            payload.get("theme", DEFAULT_THEME),
            payload.get("font", DEFAULT_FONT),
            username,
            "generate_document",
            touch_project=True,
        )

    def get_document_payload(self, project_id: str, branch: str, document_id: str, format_name: str = "json") -> Any:
        document = self.store.get_document(project_id, branch, document_id)
        if format_name == "json":
            return {"document": document}
        return self.render_document(document, format_name, missing_docx_status=404, pdf_fallback=True)

    def render_generated_document(
        self,
        payload: dict[str, Any],
        username: str,
        doc_type: str,
        audit_action: str,
        *,
        touch_project: bool = False,
        missing_docx_status: int = 422,
    ) -> Any:
        project_id = payload.get("project") or payload.get("project_id") or payload.get("model_name") or "satellite-power"
        branch = payload.get("branch") or "main"
        document = self._generate_document(
            project_id,
            branch,
            payload.get("template"),
            doc_type,
            payload.get("theme", DEFAULT_THEME),
            payload.get("font", DEFAULT_FONT),
            username,
            audit_action,
            touch_project=touch_project,
        )
        return self.render_document(document, doc_type, missing_docx_status=missing_docx_status, pdf_fallback=False)

    def _generate_document(
        self,
        project_id: str,
        branch: str,
        template: Any,
        doc_type: str,
        theme: str,
        font: str,
        username: str,
        audit_action: str,
        *,
        touch_project: bool,
    ) -> dict[str, Any]:
        project = self.store.get_project(project_id)
        document = generate_document(project, branch, template, doc_type, theme, font)
        if touch_project:
            self.store.touch_project(project_id)
            self.store.save()
        self.store.record_audit(project_id, branch, audit_action, username, document["id"])
        return document

    def render_document(
        self,
        document: dict[str, Any],
        format_name: str,
        *,
        missing_docx_status: int,
        pdf_fallback: bool,
    ) -> Any:
        if format_name == "html":
            return HTMLResponse(document["html"])
        if format_name == "markdown":
            return Response(document["markdown"], media_type="text/markdown")
        if format_name == "pdf":
            pdf_base64 = document.get("pdf_base64", "")
            pdf_bytes = (
                base64.b64decode(pdf_base64)
                if pdf_base64
                else html_to_pdf_bytes(
                    document.get("html", ""),
                    document.get("markdown", ""),
                    document.get("title", "SysML 鏂囨。"),
                )
                if pdf_fallback
                else b""
            )
            return Response(pdf_bytes, media_type="application/pdf")
        if format_name == "docx":
            docx_base64 = document.get("docx_base64", "")
            if docx_base64:
                return Response(
                    base64.b64decode(docx_base64),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            raise HTTPException(status_code=missing_docx_status, detail="DOCX not available, please regenerate this document")
        return {"document": document}

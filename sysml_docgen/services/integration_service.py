"""External integration service operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ..config import MAX_MODEL_BYTES
from ..repository_contract import RepositoryStore
from ..xmi import parse_xmi_elements


class IntegrationService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store

    def parse_sysml(self, payload: dict[str, Any]) -> dict[str, Any]:
        source_format = str(payload.get("type") or payload.get("format") or "").lower()
        content = payload.get("content") or payload.get("xmi") or payload.get("json") or ""
        filename = str(payload.get("file_path") or payload.get("filename") or "")
        if len(str(content).encode("utf-8")) > MAX_MODEL_BYTES:
            raise HTTPException(status_code=413, detail="妯″瀷鏂囦欢瓒呰繃 10MB 闄愬埗")
        if not source_format:
            source_format = "xmi" if filename.lower().endswith((".xmi", ".xml")) else "json"

        if source_format == "xmi":
            elements = parse_xmi_elements(str(content))
        else:
            raw_model = json.loads(content) if isinstance(content, str) else content
            elements_payload = raw_model.get("elements", raw_model) if isinstance(raw_model, dict) else raw_model
            elements = list(elements_payload.values()) if isinstance(elements_payload, dict) else list(elements_payload or [])

        return {
            "parsed_model": {
                "name": payload.get("model_name") or Path(filename).stem or "ParsedModel",
                "type": source_format,
                "elements": elements,
                "element_count": len(elements),
            }
        }

    def push_model(self, payload: dict[str, Any], username: str) -> dict[str, Any]:
        project_id = payload.get("project") or payload.get("project_id") or "satellite-power"
        branch = payload.get("branch") or "main"
        model = payload.get("model") or payload
        result = self.store.import_elements(project_id, branch, model, payload.get("username") or username)
        if payload.get("commit"):
            result["commit"] = self.store.commit(
                project_id,
                branch,
                payload.get("message", "MDK push model"),
                payload.get("username") or username,
            )
        return result

    def pull_model(self, project: str, branch: str, format_name: str = "json") -> Any:
        if format_name.lower() == "xmi":
            return self.store.export_branch_xmi(project, branch)
        return self.store.export_branch(project, branch)

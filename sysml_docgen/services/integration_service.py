"""External integration service operations."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from ..config import MAX_MODEL_BYTES
from ..integrations.adapters import AdapterError, list_adapters, parse_content
from ..repository_contract import RepositoryStore
from ..docgen import utc_now


class IntegrationService:
    def __init__(self, store: RepositoryStore, import_jobs: dict[str, dict[str, Any]] | None = None) -> None:
        self.store = store
        self.import_jobs = import_jobs if import_jobs is not None else {}

    def list_adapters(self) -> list[dict[str, Any]]:
        return list_adapters()

    def parse_sysml(self, payload: dict[str, Any]) -> dict[str, Any]:
        parsed = self._parse_payload(payload)
        elements = parsed.model.get("elements", [])

        return {
            "parsed_model": {
                "name": payload.get("model_name") or Path(str(payload.get("filename") or "")).stem or "ParsedModel",
                "type": parsed.model["format"],
                "adapter": parsed.report.adapter,
                "elements": elements,
                "element_count": len(elements),
            },
            "mapping_report": parsed.report.to_dict(),
        }

    def create_import_job(self, payload: dict[str, Any], username: str) -> dict[str, Any]:
        parsed = self._parse_payload(payload)
        filename = str(payload.get("file_path") or payload.get("filename") or "")
        project_id = payload.get("project") or payload.get("project_id") or "satellite-power"
        branch = payload.get("branch") or "main"
        job_id = f"IMP-{utc_now().replace(':', '').replace('-', '').replace('.', '')}-{uuid4().hex[:8]}"
        elements = parsed.model.get("elements", [])
        job = {
            "id": job_id,
            "status": "parsed",
            "project": project_id,
            "branch": branch,
            "adapter": parsed.report.adapter,
            "filename": filename,
            "created_at": utc_now(),
            "created_by": username,
            "parsed_model": {
                "name": payload.get("model_name") or Path(filename).stem or "ParsedModel",
                "type": parsed.model["format"],
                "adapter": parsed.report.adapter,
                "elements": elements,
                "element_count": len(elements),
            },
            "mapping_report": parsed.report.to_dict(),
            "model": parsed.model,
            "apply_result": None,
        }
        self.import_jobs[job_id] = job
        return {"job": public_import_job(job)}

    def get_import_job(self, job_id: str) -> dict[str, Any]:
        job = self.import_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"导入任务 {job_id} 不存在")
        return {"job": public_import_job(job)}

    def apply_import_job(self, job_id: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        job = self.import_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"导入任务 {job_id} 不存在")
        project_id = payload.get("project") or job["project"]
        branch = payload.get("branch") or job["branch"]
        model = deepcopy(job["model"])
        result = self.store.import_elements(project_id, branch, model, payload.get("username") or username)
        if payload.get("commit"):
            result["commit"] = self.store.commit(
                project_id,
                branch,
                payload.get("message", f"Apply MDK import job {job_id}"),
                payload.get("username") or username,
            )
        job["status"] = "applied"
        job["project"] = project_id
        job["branch"] = branch
        job["applied_at"] = utc_now()
        job["applied_by"] = payload.get("username") or username
        job["apply_result"] = result
        return {"job": public_import_job(job), "result": result}

    def _parse_payload(self, payload: dict[str, Any]):
        adapter_id = str(payload.get("adapter") or payload.get("tool") or payload.get("type") or payload.get("format") or "auto").lower()
        content = payload.get("content") or payload.get("xmi") or payload.get("json") or ""
        filename = str(payload.get("file_path") or payload.get("filename") or "")
        if len(str(content).encode("utf-8")) > MAX_MODEL_BYTES:
            raise HTTPException(status_code=413, detail="妯″瀷鏂囦欢瓒呰繃 10MB 闄愬埗")
        if adapter_id in {"", "auto"} and not filename:
            adapter_id = "xmi" if str(content).lstrip().startswith("<") else "json"
        try:
            parsed = parse_content(content, filename, adapter_id)
        except AdapterError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return parsed

    def push_model(self, payload: dict[str, Any], username: str) -> dict[str, Any]:
        project_id = payload.get("project") or payload.get("project_id") or "satellite-power"
        branch = payload.get("branch") or "main"
        model = payload.get("model") or payload
        if isinstance(model, dict) and "mapping_report" not in model and payload.get("mapping_report"):
            model = {**model, "mapping_report": payload["mapping_report"]}
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


def public_import_job(job: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in job.items() if key != "model"}
    return deepcopy(public)

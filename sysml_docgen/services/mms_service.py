"""Model management service operations."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import unquote

from fastapi import HTTPException

from ..config import MAX_MODEL_BYTES
from ..docgen import build_traceability
from ..metamodel import build_diagram, metamodel_payload
from ..repository_contract import RepositoryStore
from ..repository import project_summary
from ..collaboration import project_access_role
from ..views import build_view_diagram, list_view_elements, view_payload


def normalize_model_payload(model: dict[str, Any]) -> dict[str, Any]:
    if model.get("format") == "xmi" or model.get("xmi"):
        xmi_text = model.get("xmi") or model.get("content") or ""
        if len(str(xmi_text).encode("utf-8")) > MAX_MODEL_BYTES:
            raise HTTPException(status_code=413, detail="妯″瀷鏂囦欢瓒呰繃 10MB 闄愬埗")
        return {"format": "xmi", "xmi": xmi_text}

    if "elements" in model:
        encoded = json.dumps(model["elements"], ensure_ascii=False).encode("utf-8")
        if len(encoded) > MAX_MODEL_BYTES:
            raise HTTPException(status_code=413, detail="妯″瀷鏂囦欢瓒呰繃 10MB 闄愬埗")
        return {"format": "json", "elements": model["elements"]}

    element = {
        "id": model.get("id") or model.get("name"),
        "name": model.get("name") or model.get("id"),
        "type": model.get("type", "Block"),
        "stereotype": model.get("stereotype", ""),
        "description": model.get("description", ""),
        "owner": model.get("owner", ""),
        "attributes": model.get("attributes", model.get("content", {})),
        "relations": model.get("relations", []),
    }
    return {"format": "json", "elements": [element]}


def project_id_from_path(path: str) -> str:
    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "projects":
        return unquote(parts[2])
    return ""


def effective_project_role(project: dict[str, Any], identity: dict[str, str]) -> str:
    username = identity.get("username", "")
    if not project.get("owner"):
        return identity.get("role", "user")
    return project_access_role(project, username)


class MmsService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store

    def metamodel(self) -> dict[str, Any]:
        return metamodel_payload()

    def list_projects(self, username: str | None = None) -> list[dict[str, Any]]:
        if hasattr(self.store, "ensure_user_workspace") and username:
            self.store.ensure_user_workspace(username)
        return self.store.list_projects(username)

    def create_project(self, payload: dict[str, Any], username: str) -> dict[str, Any]:
        return self.store.create_project(payload, username)

    def publish_project(self, project_id: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        return self.store.publish_project(project_id, payload, username)

    def copy_shared_project(self, project_id: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        return self.store.copy_shared_project(project_id, username, payload)

    def get_project_summary(self, project_id: str) -> dict[str, Any]:
        project = self.store.get_project(project_id)
        payload = project_summary(project)
        payload["roles"] = project.get("roles", {})
        return payload

    def list_branches(self, project_id: str) -> list[dict[str, Any]]:
        return self.store.list_branches(project_id)

    def create_branch(self, project_id: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        return self.store.create_branch(project_id, payload, username)

    def merge_branch(self, project_id: str, target_branch: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        return self.store.merge_branch(
            project_id,
            target_branch,
            payload.get("source", "main"),
            username,
            bool(payload.get("force", False)),
        )

    def list_elements(
        self,
        project_id: str,
        branch: str,
        element_type: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.store.list_elements(project_id, branch, element_type, query)

    def create_element(self, project_id: str, branch: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        return self.store.upsert_element(project_id, branch, payload, username)

    def get_element(self, project_id: str, branch: str, element_id: str) -> dict[str, Any]:
        return self.store.get_element(project_id, branch, element_id)

    def update_element(
        self,
        project_id: str,
        branch: str,
        element_id: str,
        payload: dict[str, Any],
        username: str,
    ) -> dict[str, Any]:
        payload["id"] = element_id
        return self.store.upsert_element(project_id, branch, payload, username)

    def delete_element(self, project_id: str, branch: str, element_id: str, username: str) -> dict[str, Any]:
        return self.store.delete_element(project_id, branch, element_id, username)

    def commit(self, project_id: str, branch: str, message: str, username: str) -> dict[str, Any]:
        return self.store.commit(project_id, branch, message, username)

    def list_commits(self, project_id: str) -> list[dict[str, Any]]:
        return self.store.list_commits(project_id)

    def diff(self, project_id: str, branch: str, from_ref: str | None, to_ref: str | None) -> dict[str, Any]:
        return self.store.diff_commits(project_id, branch, from_ref, to_ref)

    def rollback(self, project_id: str, branch: str, commit_id: str, username: str) -> dict[str, Any]:
        return self.store.rollback(project_id, branch, commit_id, username)

    def list_tags(self, project_id: str) -> list[dict[str, Any]]:
        return self.store.list_tags(project_id)

    def create_tag(self, project_id: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        return self.store.create_tag(project_id, payload, username)

    def list_audit(self, project_id: str, limit: int = 80) -> list[dict[str, Any]]:
        return self.store.list_audit(project_id, limit)

    def import_model(self, project_id: str, branch: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        return self.store.import_elements(project_id, branch, payload, username)

    def export_model(self, project_id: str, branch: str, format_name: str = "json") -> Any:
        if format_name.lower() == "xmi":
            return self.store.export_branch_xmi(project_id, branch)
        return self.store.export_branch(project_id, branch)

    def validate_model(self, project_id: str, branch: str) -> dict[str, Any]:
        return self.store.validate_branch(project_id, branch)

    def get_model(self, model_name: str, project: str = "satellite-power", branch: str = "main") -> dict[str, Any]:
        elements = self.store.get_branch(project, branch).get("elements", {})
        if model_name in elements:
            return elements[model_name]
        exported = self.store.export_branch(project, branch)
        exported["model_name"] = model_name
        return exported

    def create_model(self, payload: dict[str, Any], username: str) -> dict[str, Any]:
        project_id = payload.get("project") or payload.get("project_id") or "satellite-power"
        branch = payload.get("branch") or "main"
        model = payload.get("model") or payload
        result = self.store.import_elements(project_id, branch, normalize_model_payload(model), username)
        if payload.get("commit", True):
            result["commit"] = self.store.commit(
                project_id,
                branch,
                payload.get("message", f"Create model {payload.get('name', project_id)}"),
                username,
            )
        return result

    def update_model(self, model_name: str, payload: dict[str, Any], username: str) -> dict[str, Any]:
        payload.setdefault("name", model_name)
        return self.create_model(payload, username)

    def delete_model(self, model_name: str, project: str, branch: str, username: str) -> dict[str, Any]:
        return self.store.delete_element(project, branch, model_name, username)

    def create_mms_branch(self, payload: dict[str, Any], username: str) -> dict[str, Any]:
        project_id = payload.get("project") or payload.get("project_id") or payload.get("model_name") or "satellite-power"
        return self.store.create_branch(project_id, payload, username)

    def list_mms_branches(self, project: str = "satellite-power") -> list[dict[str, Any]]:
        return self.store.list_branches(project)

    def diagram(self, project_id: str, branch: str, diagram_type: str = "requirements") -> dict[str, Any]:
        elements = self.store.get_branch(project_id, branch).get("elements", {})
        return build_diagram(elements, diagram_type)

    def traceability(self, project_id: str, branch: str) -> dict[str, Any]:
        elements = self.store.get_branch(project_id, branch).get("elements", {})
        return build_traceability(elements)

    def list_views(self, project_id: str, branch: str) -> list[dict[str, Any]]:
        elements = self.store.get_branch(project_id, branch).get("elements", {})
        return list_view_elements(elements)

    def view(self, project_id: str, branch: str, view_id: str) -> dict[str, Any]:
        elements = self.store.get_branch(project_id, branch).get("elements", {})
        try:
            return view_payload(elements, view_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"View {view_id} does not exist") from exc

    def view_diagram(self, project_id: str, branch: str, view_id: str) -> dict[str, Any]:
        elements = self.store.get_branch(project_id, branch).get("elements", {})
        try:
            return build_view_diagram(elements, view_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"View {view_id} does not exist") from exc

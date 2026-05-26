"""Collaboration/workspace overrides for the repository layer."""

from __future__ import annotations

import copy
import re
from typing import Any

from .docgen import utc_now
from . import store as store_module
from .store import ConflictError, ForbiddenError, ModelStore, slugify


def normalize_members(members: Any, owner: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = [{"username": owner, "role": "owner"}]
    seen = {owner}
    if isinstance(members, str):
        candidates: list[Any] = [item.strip() for item in re.split(r"[,\n;]+", members) if item.strip()]
    elif isinstance(members, list):
        candidates = members
    else:
        candidates = []
    for member in candidates:
        if isinstance(member, dict):
            username = str(member.get("username", "")).strip()
            role = str(member.get("role", "editor")).strip().lower() or "editor"
        else:
            username = str(member).strip()
            role = "editor"
        if not username or username in seen:
            continue
        if role not in {"owner", "editor", "viewer"}:
            role = "editor"
        result.append({"username": username, "role": role})
        seen.add(username)
    return result


def project_access_role(project: dict[str, Any], username: str) -> str:
    if not username:
        return ""
    if project.get("owner") == username:
        return "owner"
    if project.get("visibility") != "shared":
        return ""
    for member in project.get("members", []):
        if isinstance(member, dict) and str(member.get("username", "")) == username:
            role = str(member.get("role", "viewer")).strip().lower() or "viewer"
            return role if role in {"owner", "editor", "viewer"} else "viewer"
    return ""


def project_summary(project: dict[str, Any]) -> dict[str, Any]:
    branch_count = len(project.get("branches", {}))
    branches = project.get("branches", {})
    element_count = sum(len(branch.get("elements", {})) for branch in branches.values())
    document_count = sum(len(branch.get("documents", [])) for branch in branches.values())
    view_count = sum(
        1
        for branch in branches.values()
        for element in branch.get("elements", {}).values()
        if element.get("type") in {"View", "Viewpoint"}
    )
    members = project.get("members", [])
    return {
        "id": project.get("id", ""),
        "name": project.get("name", ""),
        "description": project.get("description", ""),
        "organization": project.get("organization", ""),
        "owner": project.get("owner", ""),
        "visibility": project.get("visibility", "private"),
        "kind": project.get("kind", "workspace"),
        "member_count": len(members) if isinstance(members, list) else 0,
        "members": copy.deepcopy(members) if isinstance(members, list) else [],
        "source_project_id": project.get("source_project_id", ""),
        "published_from": project.get("published_from", ""),
        "published_by": project.get("published_by", ""),
        "published_at": project.get("published_at", ""),
        "copied_from": project.get("copied_from", ""),
        "copied_by": project.get("copied_by", ""),
        "copied_at": project.get("copied_at", ""),
        "created_at": project.get("created_at", ""),
        "updated_at": project.get("updated_at", ""),
        "branches": branch_count,
        "elements": element_count,
        "documents": document_count,
        "views": view_count,
        "commits": len(project.get("commits", [])),
        "tags": len(project.get("tags", [])),
    }


def enforce_role(method: str, role: str) -> None:
    normalized = (role or "").strip().lower()
    if not normalized:
        raise ForbiddenError("请先登录")
    if normalized in {"user", "owner", "editor"}:
        return
    if normalized == "viewer":
        if method in {"GET", "HEAD", "OPTIONS"}:
            return
        raise ForbiddenError("当前空间只有只读权限")
    if method in {"GET", "HEAD", "OPTIONS"}:
        return
    raise ForbiddenError("当前空间没有写入权限")


def ensure_user_workspace(self: ModelStore, username: str) -> dict[str, Any]:
    owner = slugify(username)
    project_id = f"workspace-{owner}"
    existing = self.data.setdefault("projects", {}).get(project_id)
    if existing:
        existing["owner"] = username
        existing["visibility"] = "private"
        existing["kind"] = "workspace"
        existing["members"] = [{"username": username, "role": "owner"}]
        existing.setdefault("source_project_id", "")
        existing.setdefault("published_from", "")
        existing.setdefault("published_by", "")
        existing.setdefault("published_at", "")
        existing.setdefault("copied_from", "")
        existing.setdefault("copied_by", "")
        existing.setdefault("copied_at", "")
        return copy.deepcopy(existing)

    now = utc_now()
    project = {
        "id": project_id,
        "name": f"{username} 的个人工作台",
        "description": "默认空工作区，元素需要由用户自行创建或从共享空间复制。",
        "organization": username,
        "created_at": now,
        "updated_at": now,
        "visibility": "private",
        "kind": "workspace",
        "owner": username,
        "members": [{"username": username, "role": "owner"}],
        "source_project_id": "",
        "published_from": "",
        "published_by": "",
        "published_at": "",
        "copied_from": "",
        "copied_by": "",
        "copied_at": "",
        "roles": {},
        "branches": {
            "main": {
                "name": "main",
                "head": "",
                "elements": {},
                "documents": [],
                "created_at": now,
            }
        },
        "commits": [],
        "tags": [],
    }
    self._commit_in_memory(project, "main", "初始化个人工作台", username)
    self.data["projects"][project_id] = project
    self.save()
    self.record_audit(project_id, "main", "create_workspace", username, detail={"scope": "private"})
    return copy.deepcopy(project)


def list_projects(self: ModelStore, username: str | None = None) -> list[dict[str, Any]]:
    if username:
        self.ensure_user_workspace(username)
    projects = list(self.data.get("projects", {}).values())
    if username:
        projects = [project for project in projects if project_access_role(project, username)]
    return sorted(
        [project_summary(project) for project in projects],
        key=lambda item: (0 if item.get("kind") == "workspace" else 1, item["id"]),
    )


def create_project(self: ModelStore, payload: dict[str, Any], actor: str = "engineer") -> dict[str, Any]:
    project_id = slugify(payload.get("id") or payload.get("name") or "shared-project")
    if project_id in self.data.setdefault("projects", {}):
        raise ConflictError(f"项目 {project_id} 已存在")
    now = utc_now()
    members = normalize_members(payload.get("members"), actor)
    project = {
        "id": project_id,
        "name": payload.get("name") or project_id,
        "description": payload.get("description", ""),
        "organization": payload.get("organization", "共享协作组"),
        "created_at": now,
        "updated_at": now,
        "visibility": "shared",
        "kind": "shared",
        "owner": actor,
        "members": members,
        "source_project_id": "",
        "published_from": "",
        "published_by": "",
        "published_at": "",
        "copied_from": "",
        "copied_by": "",
        "copied_at": "",
        "roles": {},
        "branches": {
            "main": {
                "name": "main",
                "head": "",
                "elements": {},
                "documents": [],
                "created_at": now,
            }
        },
        "commits": [],
        "tags": [],
    }
    self._commit_in_memory(project, "main", "初始化共享项目", actor)
    self.data["projects"][project_id] = project
    self.save()
    self.record_audit(project_id, "main", "create_shared_project", actor, detail={"name": project["name"]})
    return copy.deepcopy(project)


def publish_project(
    self: ModelStore, project_id: str, payload: dict[str, Any], actor: str
) -> dict[str, Any]:
    source = self.get_project(project_id)
    if source.get("owner") != actor:
        raise ForbiddenError("Only the owner can publish a shared project")
    shared_id = slugify(payload.get("id") or payload.get("name") or f"{project_id}-shared")
    if shared_id in self.data.setdefault("projects", {}):
        raise ConflictError(f"项目 {shared_id} 已存在")
    now = utc_now()
    published = copy.deepcopy(source)
    published["id"] = shared_id
    published["name"] = payload.get("name") or f"{source.get('name', project_id)}（共享）"
    published["description"] = payload.get("description", source.get("description", ""))
    published["organization"] = payload.get("organization", source.get("organization", "共享协作组"))
    published["visibility"] = "shared"
    published["kind"] = "shared"
    published["owner"] = actor
    published["members"] = normalize_members(payload.get("members"), actor)
    published["source_project_id"] = project_id
    published["published_from"] = project_id
    published["published_by"] = actor
    published["published_at"] = now
    published["copied_from"] = ""
    published["copied_by"] = ""
    published["copied_at"] = ""
    published["created_at"] = now
    published["updated_at"] = now
    self.data["projects"][shared_id] = published
    self.save()
    self.record_audit(project_id, "main", "publish_project", actor, detail={"target": shared_id})
    self.record_audit(shared_id, "main", "create_shared_project", actor, detail={"source": project_id})
    return copy.deepcopy(published)


def copy_shared_project(
    self: ModelStore, project_id: str, actor: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    source = self.get_project(project_id)
    if source.get("visibility") != "shared":
        raise ForbiddenError("Only shared projects can be copied")
    if not project_access_role(source, actor):
        raise ForbiddenError("You do not have access to this shared project")
    payload = payload or {}
    copy_id = slugify(payload.get("id") or payload.get("name") or f"{actor}-{project_id}-copy")
    if copy_id in self.data.setdefault("projects", {}):
        raise ConflictError(f"项目 {copy_id} 已存在")
    now = utc_now()
    copied = copy.deepcopy(source)
    copied["id"] = copy_id
    copied["name"] = payload.get("name") or f"{source.get('name', project_id)}（副本）"
    copied["description"] = payload.get("description", source.get("description", ""))
    copied["organization"] = payload.get("organization", actor)
    copied["visibility"] = "private"
    copied["kind"] = "copy"
    copied["owner"] = actor
    copied["members"] = [{"username": actor, "role": "owner"}]
    copied["source_project_id"] = project_id
    copied["published_from"] = ""
    copied["published_by"] = ""
    copied["published_at"] = ""
    copied["copied_from"] = project_id
    copied["copied_by"] = actor
    copied["copied_at"] = now
    copied["created_at"] = now
    copied["updated_at"] = now
    self.data["projects"][copy_id] = copied
    self.save()
    self.record_audit(copy_id, "main", "copy_shared_project", actor, detail={"source": project_id})
    return copy.deepcopy(copied)


ModelStore.ensure_user_workspace = ensure_user_workspace
ModelStore.ensure_user_sample_project = ensure_user_workspace
ModelStore.list_projects = list_projects
ModelStore.create_project = create_project
ModelStore.publish_project = publish_project
ModelStore.copy_shared_project = copy_shared_project
store_module.normalize_members = normalize_members
store_module.project_access_role = project_access_role
store_module.project_summary = project_summary
store_module.enforce_role = enforce_role

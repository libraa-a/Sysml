"""SQLite-backed model repository for the SysML course design prototype."""

from __future__ import annotations

import copy
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .docgen import stable_hash, utc_now
from .metamodel import TYPE_PREFIX, default_stereotype, validate_element, validate_repository
from .xmi import elements_to_xmi, parse_xmi_elements


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SQLITE_PATH = DATA_DIR / "store.sqlite3"
LEGACY_JSON_PATH = DATA_DIR / "store.json"
SAMPLE_PATH = DATA_DIR / "sample_project.json"
SCHEMA_VERSION = "2.1"


class StoreError(Exception):
    status_code = 400


class NotFoundError(StoreError):
    status_code = 404


class ConflictError(StoreError):
    status_code = 409


class ForbiddenError(StoreError):
    status_code = 403


class ModelStore:
    def __init__(self, path: Path = SQLITE_PATH) -> None:
        self.path = path
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.data = self._load()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def connection(self) -> Any:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS element_index (
                    project_id TEXT NOT NULL,
                    branch_name TEXT NOT NULL,
                    element_id TEXT NOT NULL,
                    element_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (project_id, branch_name, element_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    branch_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    element_id TEXT,
                    created_at TEXT NOT NULL,
                    detail TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_element_index_type ON element_index(project_id, branch_name, element_type)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_events(project_id, created_at)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    display TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _load(self) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute("SELECT payload FROM state WHERE key = 'model'").fetchone()
            if row:
                data = json.loads(row["payload"])
            else:
                data = self._load_seed()
                self.data = data
                self.save()
        self._upgrade_data(data)
        self.data = data
        self.save()
        return data

    def _load_seed(self) -> dict[str, Any]:
        seed_path = LEGACY_JSON_PATH if LEGACY_JSON_PATH.exists() else SAMPLE_PATH
        with seed_path.open("r", encoding="utf-8") as source:
            return json.load(source)

    def _sample_data(self) -> dict[str, Any]:
        with SAMPLE_PATH.open("r", encoding="utf-8") as source:
            return json.load(source)

    def _upgrade_data(self, data: dict[str, Any]) -> None:
        refresh_sample_elements = data.get("schema_version") != SCHEMA_VERSION
        data.setdefault("schema_version", SCHEMA_VERSION)
        data.setdefault("projects", {})
        sample = self._sample_data()

        for project_id, sample_project in sample.get("projects", {}).items():
            project = data["projects"].setdefault(project_id, copy.deepcopy(sample_project))
            project.setdefault("branches", {})
            project.setdefault("commits", [])
            project.setdefault("tags", [])
            project.setdefault("roles", sample_project.get("roles", {}))
            for branch_name, sample_branch in sample_project.get("branches", {}).items():
                branch = project["branches"].setdefault(branch_name, copy.deepcopy(sample_branch))
                branch.setdefault("documents", [])
                branch.setdefault("elements", {})
                for element_id, sample_element in sample_branch.get("elements", {}).items():
                    if refresh_sample_elements:
                        branch["elements"][element_id] = copy.deepcopy(sample_element)
                    else:
                        branch["elements"].setdefault(element_id, copy.deepcopy(sample_element))

        for project in data.get("projects", {}).values():
            project.setdefault("roles", {"admin": ["teacher"], "author": ["engineer"], "reader": ["reviewer"]})
            project.setdefault("commits", [])
            project.setdefault("tags", [])
            for branch in project.get("branches", {}).values():
                branch.setdefault("documents", [])
                branch.setdefault("elements", {})
                head = branch.get("head")
                for commit in project.get("commits", []):
                    if commit.get("id") == head and not commit.get("snapshot"):
                        commit["snapshot"] = copy.deepcopy(branch.get("elements", {}))
                        commit["element_count"] = len(commit["snapshot"])
                        commit["model_hash"] = stable_hash(commit["snapshot"])
            if not project.get("commits"):
                for branch_name in project.get("branches", {}):
                    self._commit_in_memory(project, branch_name, "初始化项目", "system")
        data["schema_version"] = SCHEMA_VERSION

    def save(self) -> None:
        payload = json.dumps(self.data, ensure_ascii=False, indent=2)
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO state(key, payload, updated_at)
                VALUES('model', ?, ?)
                ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (payload, utc_now()),
            )
            connection.execute("DELETE FROM element_index")
            for project_id, project in self.data.get("projects", {}).items():
                for branch_name, branch in project.get("branches", {}).items():
                    for element in branch.get("elements", {}).values():
                        connection.execute(
                            """
                            INSERT INTO element_index(
                                project_id, branch_name, element_id, element_type, name, owner, updated_at, payload
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                project_id,
                                branch_name,
                                element.get("id", ""),
                                element.get("type", ""),
                                element.get("name", ""),
                                element.get("owner", ""),
                                element.get("updated_at", ""),
                                json.dumps(element, ensure_ascii=False),
                            ),
                        )

    def record_audit(
        self,
        project_id: str,
        branch_name: str,
        action: str,
        actor: str,
        element_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO audit_events(project_id, branch_name, action, actor, element_id, created_at, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    branch_name,
                    action,
                    actor,
                    element_id,
                    utc_now(),
                    json.dumps(detail or {}, ensure_ascii=False),
                ),
            )

    def list_audit(self, project_id: str, limit: int = 80) -> list[dict[str, Any]]:
        self.get_project(project_id)
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, branch_name, action, actor, element_id, created_at, detail
                FROM audit_events
                WHERE project_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["detail"] = json.loads(item["detail"])
            result.append(item)
        return result

    def get_user(self, username: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT username, password_hash, role, display, created_at FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if not row:
            return None
        return {
            "username": row["username"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "display": row["display"],
            "created_at": row["created_at"],
        }

    def create_user(
        self,
        username: str,
        password_hash: str,
        role: str,
        display: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        created_at = created_at or utc_now()
        with self.connection() as connection:
            try:
                connection.execute(
                    "INSERT INTO users(username, password_hash, role, display, created_at) VALUES (?, ?, ?, ?, ?)",
                    (username, password_hash, role, display, created_at),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(f"用户名 '{username}' 已存在") from exc
        return {
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "display": display,
            "created_at": created_at,
        }

    def list_projects(self) -> list[dict[str, Any]]:
        return sorted(
            [project_summary(project) for project in self.data.get("projects", {}).values()],
            key=lambda item: item["id"],
        )

    def create_project(self, payload: dict[str, Any], actor: str = "engineer") -> dict[str, Any]:
        project_id = slugify(payload.get("id") or payload.get("name") or "project")
        if project_id in self.data.setdefault("projects", {}):
            raise ConflictError(f"项目 {project_id} 已存在")
        now = utc_now()
        project = {
            "id": project_id,
            "name": payload.get("name") or project_id,
            "description": payload.get("description", ""),
            "organization": payload.get("organization", "课程设计小组"),
            "created_at": now,
            "updated_at": now,
            "roles": normalized_roles(payload.get("roles")),
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
        self.data["projects"][project_id] = project
        self._commit_in_memory(project, "main", "初始化项目", actor)
        self.save()
        self.record_audit(project_id, "main", "create_project", actor, detail={"name": project["name"]})
        return copy.deepcopy(project)

    def get_project(self, project_id: str) -> dict[str, Any]:
        try:
            return self.data["projects"][project_id]
        except KeyError as exc:
            raise NotFoundError(f"项目 {project_id} 不存在") from exc

    def get_branch(self, project_id: str, branch_name: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        try:
            return project["branches"][branch_name]
        except KeyError as exc:
            raise NotFoundError(f"分支 {branch_name} 不存在") from exc

    def list_branches(self, project_id: str) -> list[dict[str, Any]]:
        project = self.get_project(project_id)
        return [
            {
                "name": branch["name"],
                "head": branch.get("head", ""),
                "elements": len(branch.get("elements", {})),
                "documents": len(branch.get("documents", [])),
                "created_at": branch.get("created_at", ""),
            }
            for branch in project.get("branches", {}).values()
        ]

    def create_branch(self, project_id: str, payload: dict[str, Any], actor: str = "engineer") -> dict[str, Any]:
        project = self.get_project(project_id)
        source_name = payload.get("source", "main")
        source = self.get_branch(project_id, source_name)
        branch_name = slugify(payload.get("name") or "branch")
        if branch_name in project["branches"]:
            raise ConflictError(f"分支 {branch_name} 已存在")
        branch = copy.deepcopy(source)
        branch["name"] = branch_name
        branch["created_at"] = utc_now()
        branch["documents"] = []
        project["branches"][branch_name] = branch
        project["updated_at"] = utc_now()
        self.save()
        self.record_audit(project_id, branch_name, "create_branch", actor, detail={"source": source_name})
        return copy.deepcopy(branch)

    def list_elements(
        self,
        project_id: str,
        branch_name: str,
        element_type: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        self.get_branch(project_id, branch_name)
        sql = """
            SELECT payload FROM element_index
            WHERE project_id = ? AND branch_name = ?
        """
        params: list[Any] = [project_id, branch_name]
        if element_type:
            sql += " AND element_type = ?"
            params.append(element_type)
        if query:
            sql += " AND (LOWER(element_id) LIKE ? OR LOWER(name) LIKE ? OR LOWER(payload) LIKE ?)"
            q = f"%{query.lower()}%"
            params.extend([q, q, q])
        sql += " ORDER BY element_type, element_id"
        with self.connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def get_element(self, project_id: str, branch_name: str, element_id: str) -> dict[str, Any]:
        branch = self.get_branch(project_id, branch_name)
        try:
            return branch["elements"][element_id]
        except KeyError as exc:
            raise NotFoundError(f"模型元素 {element_id} 不存在") from exc

    def upsert_element(
        self,
        project_id: str,
        branch_name: str,
        payload: dict[str, Any],
        actor: str = "engineer",
    ) -> dict[str, Any]:
        branch = self.get_branch(project_id, branch_name)
        element_type = payload.get("type", "Requirement")
        element_id = payload.get("id") or self.next_element_id(branch, element_type)
        existing = branch.setdefault("elements", {}).get(element_id, {})
        now = utc_now()
        element = {
            "id": element_id,
            "name": payload.get("name", existing.get("name", element_id)),
            "type": element_type,
            "stereotype": payload.get("stereotype", existing.get("stereotype", default_stereotype(element_type))),
            "description": payload.get("description", existing.get("description", "")),
            "owner": payload.get("owner", existing.get("owner", "")),
            "attributes": payload.get("attributes", existing.get("attributes", {})),
            "relations": normalize_relations(payload.get("relations", existing.get("relations", []))),
            "updated_at": now,
            "created_at": existing.get("created_at", now),
        }
        issues = validate_element(element, {**branch.get("elements", {}), element_id: element})
        if any(item["severity"] == "error" for item in issues):
            raise StoreError("; ".join(item["message"] for item in issues if item["severity"] == "error"))
        branch["elements"][element_id] = element
        self.touch_project(project_id, save=False)
        self.save()
        self.record_audit(
            project_id,
            branch_name,
            "update_element" if existing else "create_element",
            actor,
            element_id,
            {"type": element_type, "name": element["name"]},
        )
        return copy.deepcopy(element)

    def delete_element(
        self,
        project_id: str,
        branch_name: str,
        element_id: str,
        actor: str = "engineer",
    ) -> dict[str, str]:
        branch = self.get_branch(project_id, branch_name)
        if element_id not in branch.get("elements", {}):
            raise NotFoundError(f"模型元素 {element_id} 不存在")
        deleted = branch["elements"][element_id]
        del branch["elements"][element_id]
        for element in branch.get("elements", {}).values():
            element["relations"] = [
                relation for relation in element.get("relations", []) if relation.get("target") != element_id
            ]
        self.touch_project(project_id, save=False)
        self.save()
        self.record_audit(project_id, branch_name, "delete_element", actor, element_id, {"name": deleted.get("name")})
        return {"deleted": element_id}

    def import_elements(
        self,
        project_id: str,
        branch_name: str,
        payload: dict[str, Any],
        actor: str = "engineer",
    ) -> dict[str, Any]:
        source_format = str(payload.get("format", "json")).lower()
        mapping_report = payload.get("mapping_report") or payload.get("report")
        is_xmi_import = source_format == "xmi" or payload.get("xmi")
        provided_elements = payload.get("elements")
        if is_xmi_import and provided_elements is not None:
            elements = provided_elements
        elif is_xmi_import:
            xmi_text = payload.get("xmi") or payload.get("content") or payload.get("text") or ""
            if not isinstance(xmi_text, str) or not xmi_text.strip():
                raise StoreError("XMI 导入数据不能为空")
            elements = parse_xmi_elements(xmi_text)
        else:
            elements = provided_elements
        if isinstance(elements, dict):
            iterable = elements.values()
        elif isinstance(elements, list):
            iterable = elements
        else:
            raise StoreError("导入数据需要 elements 数组或对象")
        imported = []
        parsed_elements = [copy.deepcopy(element) for element in iterable]
        for element in parsed_elements:
            element_without_relations = copy.deepcopy(element)
            element_without_relations["relations"] = []
            self.upsert_element(project_id, branch_name, element_without_relations, actor)
        for element in parsed_elements:
            imported.append(self.upsert_element(project_id, branch_name, element, actor))
        self.record_audit(
            project_id,
            branch_name,
            "import_elements",
            actor,
            detail={"count": len(imported), "format": source_format, "mapping_report": mapping_report},
        )
        return {"imported": len(imported), "format": source_format, "elements": imported, "mapping_report": mapping_report}

    def export_branch(self, project_id: str, branch_name: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        branch = self.get_branch(project_id, branch_name)
        return {
            "project": project_summary(project),
            "branch": branch_name,
            "head": branch.get("head", ""),
            "exported_at": utc_now(),
            "elements": copy.deepcopy(branch.get("elements", {})),
        }

    def export_branch_xmi(self, project_id: str, branch_name: str) -> str:
        return elements_to_xmi(self.export_branch(project_id, branch_name))

    def next_element_id(self, branch: dict[str, Any], element_type: str) -> str:
        prefix = TYPE_PREFIX.get(element_type, "ELM")
        highest = 0
        for element_id in branch.get("elements", {}):
            match = re.match(rf"^{re.escape(prefix)}-(\d+)$", element_id)
            if match:
                highest = max(highest, int(match.group(1)))
        return f"{prefix}-{highest + 1:03d}"

    def commit(
        self,
        project_id: str,
        branch_name: str,
        message: str,
        author: str = "engineer",
    ) -> dict[str, Any]:
        project = self.get_project(project_id)
        commit = self._commit_in_memory(project, branch_name, message, author)
        self.save()
        self.record_audit(project_id, branch_name, "commit", author, detail=without_snapshot(commit))
        return without_snapshot(commit)

    def _commit_in_memory(
        self,
        project: dict[str, Any],
        branch_name: str,
        message: str,
        author: str,
    ) -> dict[str, Any]:
        branch = project["branches"][branch_name]
        snapshot = copy.deepcopy(branch.get("elements", {}))
        commit_id = f"C-{len(project.get('commits', [])) + 1:04d}-{stable_hash(snapshot)[:6]}"
        commit = {
            "id": commit_id,
            "branch": branch_name,
            "message": message or "保存模型快照",
            "author": author,
            "created_at": utc_now(),
            "model_hash": stable_hash(snapshot),
            "element_count": len(snapshot),
            "snapshot": snapshot,
        }
        project.setdefault("commits", []).insert(0, commit)
        branch["head"] = commit_id
        project["updated_at"] = utc_now()
        return commit

    def list_commits(self, project_id: str) -> list[dict[str, Any]]:
        project = self.get_project(project_id)
        return [without_snapshot(commit) for commit in project.get("commits", [])]

    def find_commit(self, project_id: str, commit_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        for commit in project.get("commits", []):
            if commit.get("id") == commit_id:
                return commit
        raise NotFoundError(f"提交 {commit_id} 不存在")

    def find_tag(self, project_id: str, tag_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        normalized_tag_id = slugify(tag_id)
        for tag in project.get("tags", []):
            if tag.get("id") == tag_id or tag.get("id") == normalized_tag_id or tag.get("name") == tag_id:
                return tag
        raise NotFoundError(f"Tag {tag_id} does not exist")

    def snapshot_for_ref(self, project_id: str, branch_name: str, ref: str | None) -> dict[str, Any]:
        branch = self.get_branch(project_id, branch_name)
        if not ref or ref == "working":
            return copy.deepcopy(branch.get("elements", {}))
        if ref.startswith("tag:"):
            tag = self.find_tag(project_id, ref.removeprefix("tag:"))
            return copy.deepcopy(self.find_commit(project_id, tag.get("commit", "")).get("snapshot", {}))
        try:
            return copy.deepcopy(self.find_commit(project_id, ref).get("snapshot", {}))
        except NotFoundError:
            tag = self.find_tag(project_id, ref)
            return copy.deepcopy(self.find_commit(project_id, tag.get("commit", "")).get("snapshot", {}))

    def diff_commits(
        self,
        project_id: str,
        branch_name: str,
        from_ref: str | None,
        to_ref: str | None,
    ) -> dict[str, Any]:
        before = self.snapshot_for_ref(project_id, branch_name, from_ref)
        after = self.snapshot_for_ref(project_id, branch_name, to_ref or "working")
        diff = diff_snapshots(before, after)
        diff["from"] = from_ref or "working"
        diff["to"] = to_ref or "working"
        return diff

    def rollback(
        self,
        project_id: str,
        branch_name: str,
        commit_id: str,
        actor: str = "engineer",
    ) -> dict[str, Any]:
        project = self.get_project(project_id)
        branch = self.get_branch(project_id, branch_name)
        commit = self.find_commit(project_id, commit_id)
        branch["elements"] = copy.deepcopy(commit.get("snapshot", {}))
        new_commit = self._commit_in_memory(project, branch_name, f"回滚到 {commit_id}", actor)
        self.save()
        self.record_audit(
            project_id,
            branch_name,
            "rollback",
            actor,
            detail={"target_commit": commit_id, "new_commit": new_commit["id"]},
        )
        return {"rolled_back_to": commit_id, "commit": without_snapshot(new_commit)}

    def merge_branch(
        self,
        project_id: str,
        target_branch: str,
        source_branch: str,
        actor: str = "engineer",
        force: bool = False,
    ) -> dict[str, Any]:
        project = self.get_project(project_id)
        target = self.get_branch(project_id, target_branch)
        source = self.get_branch(project_id, source_branch)
        target_elements = target.setdefault("elements", {})
        additions = []
        updates = []
        conflicts = []
        for element_id, source_element in source.get("elements", {}).items():
            if element_id not in target_elements:
                additions.append(element_id)
                continue
            if stable_hash(target_elements[element_id]) != stable_hash(source_element):
                conflicts.append(
                    {
                        "id": element_id,
                        "target_hash": stable_hash(target_elements[element_id]),
                        "source_hash": stable_hash(source_element),
                    }
                )
                if force:
                    updates.append(element_id)
        if conflicts and not force:
            return {"merged": False, "conflicts": conflicts, "additions": additions, "updates": updates}
        for element_id in additions + updates:
            target_elements[element_id] = copy.deepcopy(source["elements"][element_id])
        new_commit = self._commit_in_memory(project, target_branch, f"合并分支 {source_branch}", actor)
        self.save()
        self.record_audit(
            project_id,
            target_branch,
            "merge_branch",
            actor,
            detail={"source": source_branch, "additions": additions, "updates": updates, "conflicts": conflicts},
        )
        return {
            "merged": True,
            "conflicts": conflicts,
            "additions": additions,
            "updates": updates,
            "commit": without_snapshot(new_commit),
        }

    def create_tag(self, project_id: str, payload: dict[str, Any], actor: str = "engineer") -> dict[str, Any]:
        project = self.get_project(project_id)
        tag_id = slugify(payload.get("id") or payload.get("name") or "tag")
        if any(tag.get("id") == tag_id for tag in project.get("tags", [])):
            raise ConflictError(f"标签 {tag_id} 已存在")
        commit_id = payload.get("commit") or next(iter(project.get("commits", [])), {}).get("id", "")
        commit = self.find_commit(project_id, commit_id) if commit_id else {}
        tag = {
            "id": tag_id,
            "name": payload.get("name", tag_id),
            "commit": commit_id,
            "description": payload.get("description", ""),
            "author": actor,
            "model_hash": commit.get("model_hash", ""),
            "element_count": commit.get("element_count", 0),
            "created_at": utc_now(),
        }
        project.setdefault("tags", []).insert(0, tag)
        self.touch_project(project_id, save=False)
        self.save()
        self.record_audit(project_id, "", "create_tag", actor, detail=tag)
        return copy.deepcopy(tag)

    def list_tags(self, project_id: str) -> list[dict[str, Any]]:
        project = self.get_project(project_id)
        return copy.deepcopy(project.get("tags", []))

    def list_documents(self, project_id: str, branch_name: str) -> list[dict[str, Any]]:
        branch = self.get_branch(project_id, branch_name)
        return [
            {
                "id": document["id"],
                "title": document["title"],
                "created_at": document["created_at"],
                "source_branch": document["source_branch"],
                "source_commit": document["source_commit"],
                "model_hash": document["model_hash"],
            }
            for document in branch.get("documents", [])
        ]

    def get_document(self, project_id: str, branch_name: str, document_id: str) -> dict[str, Any]:
        branch = self.get_branch(project_id, branch_name)
        for document in branch.get("documents", []):
            if document.get("id") == document_id:
                return document
        raise NotFoundError(f"文档 {document_id} 不存在")

    def validate_branch(self, project_id: str, branch_name: str) -> dict[str, Any]:
        branch = self.get_branch(project_id, branch_name)
        return validate_repository(branch.get("elements", {}))

    def touch_project(self, project_id: str, save: bool = True) -> None:
        project = self.get_project(project_id)
        project["updated_at"] = utc_now()
        if save:
            self.save()


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_ids = set(before)
    after_ids = set(after)
    added = [compact_element(after[element_id]) for element_id in sorted(after_ids - before_ids)]
    removed = [compact_element(before[element_id]) for element_id in sorted(before_ids - after_ids)]
    modified = []
    for element_id in sorted(before_ids & after_ids):
        if stable_hash(before[element_id]) == stable_hash(after[element_id]):
            continue
        modified.append(
            {
                "id": element_id,
                "name": after[element_id].get("name", before[element_id].get("name", "")),
                "type": after[element_id].get("type", before[element_id].get("type", "")),
                "changes": field_changes(before[element_id], after[element_id]),
            }
        )
    return {
        "summary": {"added": len(added), "removed": len(removed), "modified": len(modified)},
        "added": added,
        "removed": removed,
        "modified": modified,
    }


def field_changes(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    fields = ["name", "type", "stereotype", "description", "owner", "attributes", "relations"]
    changes = []
    for field in fields:
        if before.get(field) != after.get(field):
            changes.append({"field": field, "before": before.get(field), "after": after.get(field)})
    return changes


def compact_element(element: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(element.get("id", "")),
        "name": str(element.get("name", "")),
        "type": str(element.get("type", "")),
    }


def normalize_relations(relations: Any) -> list[dict[str, str]]:
    normalized = []
    if not isinstance(relations, list):
        return normalized
    for relation in relations:
        if not isinstance(relation, dict):
            continue
        relation_type = str(relation.get("type", "")).strip()
        target = str(relation.get("target", "")).strip()
        if relation_type and target:
            normalized.append({"type": relation_type, "target": target})
    return normalized


def project_summary(project: dict[str, Any]) -> dict[str, Any]:
    branch_count = len(project.get("branches", {}))
    element_count = sum(len(branch.get("elements", {})) for branch in project.get("branches", {}).values())
    return {
        "id": project.get("id", ""),
        "name": project.get("name", ""),
        "description": project.get("description", ""),
        "organization": project.get("organization", ""),
        "created_at": project.get("created_at", ""),
        "updated_at": project.get("updated_at", ""),
        "branches": branch_count,
        "elements": element_count,
        "commits": len(project.get("commits", [])),
        "tags": len(project.get("tags", [])),
    }


def without_snapshot(commit: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in commit.items() if key != "snapshot"}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def normalized_roles(roles: Any) -> dict[str, list[str]]:
    defaults = {"admin": ["teacher"], "author": ["engineer"], "reader": ["reviewer"]}
    if not isinstance(roles, dict):
        return defaults
    normalized = {}
    for role, default_users in defaults.items():
        users = roles.get(role, default_users)
        normalized[role] = [str(user) for user in users] if isinstance(users, list) else default_users
    return normalized


def enforce_role(method: str, role: str) -> None:
    normalized = (role or "author").lower()
    if method in {"GET", "HEAD", "OPTIONS"}:
        if normalized not in {"admin", "author", "reader"}:
            raise ForbiddenError("当前角色没有读取权限")
    elif normalized not in {"admin", "author"}:
        raise ForbiddenError("当前角色没有写入权限")

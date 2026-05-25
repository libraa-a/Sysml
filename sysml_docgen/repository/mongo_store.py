"""MongoDB-backed repository implementation."""

from __future__ import annotations

import copy
import json
from typing import Any

from ..docgen import utc_now
from .sqlite_store import ConflictError, ModelStore, SQLITE_PATH


class MongoModelStore(ModelStore):
    """MongoDB-backed MMS repository with the same contract as ModelStore."""

    def __init__(self, uri: str, database: str = "sysml_docgen", collection: str = "repository") -> None:
        try:
            from pymongo import ASCENDING, MongoClient
        except ImportError as exc:  # pragma: no cover - optional deployment dependency
            raise RuntimeError("pymongo is required for MongoDB storage") from exc

        self.client = MongoClient(uri, serverSelectionTimeoutMS=1500)
        self.client.admin.command("ping")
        self.db = self.client[database]
        self.state_collection = self.db[collection]
        self.element_collection = self.db["element_index"]
        self.audit_collection = self.db["audit_events"]
        self.user_collection = self.db["users"]
        self.ASCENDING = ASCENDING
        super().__init__(SQLITE_PATH)

    def _init_db(self) -> None:
        self.state_collection.create_index("key", unique=True)
        self.user_collection.create_index("username", unique=True)
        self.element_collection.create_index(
            [
                ("project_id", self.ASCENDING),
                ("branch_name", self.ASCENDING),
                ("element_id", self.ASCENDING),
            ],
            unique=True,
        )
        self.element_collection.create_index(
            [
                ("project_id", self.ASCENDING),
                ("branch_name", self.ASCENDING),
                ("element_type", self.ASCENDING),
            ]
        )
        self.audit_collection.create_index([("project_id", self.ASCENDING), ("created_at", self.ASCENDING)])

    def _load(self) -> dict[str, Any]:
        row = self.state_collection.find_one({"key": "model"})
        if row:
            data = row["payload"]
        else:
            data = self._load_seed()
            self.data = data
            self.save()
        self._upgrade_data(data)
        self.data = data
        self.save()
        return data

    def save(self) -> None:
        self.state_collection.update_one(
            {"key": "model"},
            {"$set": {"payload": copy.deepcopy(self.data), "updated_at": utc_now()}},
            upsert=True,
        )
        from pymongo import ReplaceOne

        operations = []
        for project_id, project in self.data.get("projects", {}).items():
            for branch_name, branch in project.get("branches", {}).items():
                for element in branch.get("elements", {}).values():
                    operations.append(
                        ReplaceOne(
                            {
                                "project_id": project_id,
                                "branch_name": branch_name,
                                "element_id": element.get("id", ""),
                            },
                            {
                                "project_id": project_id,
                                "branch_name": branch_name,
                                "element_id": element.get("id", ""),
                                "element_type": element.get("type", ""),
                                "name": element.get("name", ""),
                                "owner": element.get("owner", ""),
                                "updated_at": element.get("updated_at", ""),
                                "payload": copy.deepcopy(element),
                            },
                            upsert=True,
                        )
                    )
        self.element_collection.delete_many({})
        if operations:
            self.element_collection.bulk_write(operations)

    def record_audit(
        self,
        project_id: str,
        branch_name: str,
        action: str,
        actor: str,
        element_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.audit_collection.insert_one(
            {
                "project_id": project_id,
                "branch_name": branch_name,
                "action": action,
                "actor": actor,
                "element_id": element_id,
                "created_at": utc_now(),
                "detail": copy.deepcopy(detail or {}),
            }
        )

    def list_audit(self, project_id: str, limit: int = 80) -> list[dict[str, Any]]:
        self.get_project(project_id)
        rows = self.audit_collection.find({"project_id": project_id}).sort("_id", -1).limit(limit)
        result = []
        for row in rows:
            row.pop("_id", None)
            result.append(row)
        return result

    def get_user(self, username: str) -> dict[str, Any] | None:
        row = self.user_collection.find_one({"username": username})
        if row is None:
            return None
        row.pop("_id", None)
        return row

    def create_user(
        self,
        username: str,
        password_hash: str,
        role: str,
        display: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        created_at = created_at or utc_now()
        try:
            self.user_collection.insert_one(
                {
                    "username": username,
                    "password_hash": password_hash,
                    "role": role,
                    "display": display,
                    "created_at": created_at,
                }
            )
        except Exception as exc:
            if "duplicate key" in str(exc).lower() or "e11000" in str(exc).lower():
                raise ConflictError(f"用户名 '{username}' 已存在") from exc
            raise
        return {
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "display": display,
            "created_at": created_at,
        }

    def list_elements(
        self,
        project_id: str,
        branch_name: str,
        element_type: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        self.get_branch(project_id, branch_name)
        filter_query: dict[str, Any] = {"project_id": project_id, "branch_name": branch_name}
        if element_type:
            filter_query["element_type"] = element_type
        rows = self.element_collection.find(filter_query).sort([("element_type", 1), ("element_id", 1)])
        elements = [copy.deepcopy(row["payload"]) for row in rows]
        if query:
            needle = query.lower()
            elements = [
                element
                for element in elements
                if needle in json.dumps(element, ensure_ascii=False).lower()
                or needle in str(element.get("id", "")).lower()
                or needle in str(element.get("name", "")).lower()
            ]
        return elements

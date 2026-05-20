"""Repository backend selection."""

from __future__ import annotations

import os

from .mongo_store import MongoModelStore
from .sqlite_store import ModelStore


def create_model_store() -> ModelStore:
    backend = os.environ.get("SYSML_STORAGE", "sqlite").lower()
    if backend in {"mongo", "mongodb"}:
        try:
            return MongoModelStore(
                os.environ.get("MONGO_URL", "mongodb://127.0.0.1:27017"),
                os.environ.get("MONGO_DB", "sysml_docgen"),
                os.environ.get("MONGO_COLLECTION", "repository"),
            )
        except Exception:
            if os.environ.get("SYSML_MONGO_STRICT", "").lower() in {"1", "true", "yes"}:
                raise
    return ModelStore()

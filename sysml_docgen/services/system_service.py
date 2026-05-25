"""System, health, and authentication service operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..auth import login, register
from ..config import FONT_PRESETS, FRONTEND_DIST_DIR, MAX_MODEL_BYTES, OUTPUT_DIR, PANDOC_PATH, PDF_ENGINE, QUARTO_PATH, THEME_PRESETS
from ..docgen import pandoc_available, quarto_available
from ..ops import metrics_payload
from ..repository_contract import RepositoryStore


class SystemService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store

    def health_payload(
        self,
        identity: dict[str, str],
        frontend_dir: Path | None,
        frontend_mode: str,
    ) -> dict[str, Any]:
        backend = "mongodb" if self.store.__class__.__name__ == "MongoModelStore" else "sqlite"
        return {
            "status": "ok",
            "service": "SysML DocGen MMS",
            "version": "3.0",
            "framework": "fastapi",
            "storage": backend,
            "components": ["MMS", "MDK", "DocGen", "VE"],
            "capabilities": {
                "model_exchange": ["json", "xmi"],
                "document_formats": ["html", "markdown", "pdf", "docx"],
                "pdf_engine": PDF_ENGINE,
                "pandoc": pandoc_available(),
                "pandoc_path": PANDOC_PATH,
                "quarto": quarto_available(),
                "quarto_path": QUARTO_PATH,
                "max_model_bytes": MAX_MODEL_BYTES,
                "output_dir": str(OUTPUT_DIR),
                "openapi": "/docs",
                "access_control": "project roles: admin / author / reader",
                "frontend": frontend_mode,
                "frontend_dir": str(frontend_dir) if frontend_dir else "",
                "frontend_ready": frontend_dir is not None,
                "frontend_expected_dist": str(FRONTEND_DIST_DIR),
                "themes": list(THEME_PRESETS.keys()),
                "fonts": list(FONT_PRESETS.keys()),
            },
            "identity": identity,
        }

    def ready_payload(self, frontend_dir: Path | None, frontend_mode: str) -> dict[str, Any]:
        return {
            "ready": True,
            "storage": "mongodb" if self.store.__class__.__name__ == "MongoModelStore" else "sqlite",
            "projects": len(self.store.list_projects()),
            "frontend": str(frontend_dir) if frontend_dir else "",
            "frontend_mode": frontend_mode,
            "frontend_ready": frontend_dir is not None,
            "outputs": str(OUTPUT_DIR),
        }

    def metrics_text(self) -> str:
        return metrics_payload()

    def login(self, username: str, password: str) -> dict[str, Any] | None:
        return login(self.store, username, password)

    def register(
        self,
        username: str,
        password: str,
        role: str = "author",
        display: str | None = None,
    ) -> dict[str, Any] | None:
        return register(self.store, username, password, role=role, display=display)

"""Reusable MDK client and adapters for external engineering tools."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .integrations.adapters import (
    SUPPORTED_TOOLS,
    AdapterError,
    list_adapters,
    load_model_result as adapter_load_model_result,
    parse_content,
)


DEFAULT_SERVER = "http://127.0.0.1:8000"
DEFAULT_PROJECT = "satellite-power"
DEFAULT_BRANCH = "main"


class MdkError(RuntimeError):
    """Raised when a tool model cannot be converted or synchronized."""


@dataclass(slots=True)
class MdkConfig:
    server: str = DEFAULT_SERVER
    project: str = DEFAULT_PROJECT
    branch: str = DEFAULT_BRANCH
    username: str = "engineer"
    role: str = "author"
    token: str = ""
    timeout: int = 20


class MdkClient:
    """HTTP client shared by CLI, notebooks, MATLAB, and plugin wrappers."""

    def __init__(self, config: MdkConfig | None = None) -> None:
        self.config = config or MdkConfig()

    def health(self) -> dict[str, Any]:
        return self.request_json("GET", "/api/health")

    def parse_file(self, file_path: str | Path, tool: str = "auto") -> dict[str, Any]:
        model = load_model_file(file_path, tool)
        return {
            "parsed_model": {
                "name": Path(file_path).stem,
                "type": model["format"],
                "tool": model.get("source", {}).get("tool", model["format"]),
                "elements": model.get("elements", []),
                "element_count": len(model.get("elements", [])),
            }
        }

    def push_file(
        self,
        file_path: str | Path,
        tool: str = "auto",
        commit: bool = False,
        message: str = "MDK sync commit",
        validate: bool = False,
    ) -> dict[str, Any]:
        model = load_model_file(file_path, tool)
        result = self.push_model(model, commit=commit, message=message)
        if validate:
            result["validation"] = self.validate()
        return result

    def push_model(
        self,
        model: dict[str, Any],
        commit: bool = False,
        message: str = "MDK sync commit",
    ) -> dict[str, Any]:
        payload = {
            "project": self.config.project,
            "branch": self.config.branch,
            "username": self.config.username,
            "commit": commit,
            "message": message,
            "model": model,
        }
        return self.request_json("POST", "/api/mdk/push", payload)

    def push_elements(
        self,
        elements: list[dict[str, Any]],
        tool: str = "jupyter",
        commit: bool = True,
        message: str = "Jupyter analysis sync",
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.push_model(
            {
                "format": "json",
                "elements": elements,
                "source": source or {"tool": tool},
            },
            commit=commit,
            message=message,
        )

    def pull_model(self, output_format: str = "json") -> str | dict[str, Any]:
        query = urlencode(
            {
                "project": self.config.project,
                "branch": self.config.branch,
                "format": output_format,
            }
        )
        raw = self.request_bytes("GET", f"/api/mdk/pull?{query}")
        if output_format == "xmi":
            return raw.decode("utf-8")
        return json.loads(raw.decode("utf-8"))

    def validate(self) -> dict[str, Any]:
        return self.request_json(
            "GET",
            f"/api/projects/{self.config.project}/branches/{self.config.branch}/validate",
        )

    def generate_document(self, output_format: str = "html", template: str | None = None) -> dict[str, Any]:
        return self.request_json(
            "POST",
            f"/api/projects/{self.config.project}/branches/{self.config.branch}/documents",
            {"template": template, "format": output_format},
        )["document"]

    def request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return json.loads(self.request_bytes(method, path, payload).decode("utf-8"))

    def request_bytes(self, method: str, path: str, payload: dict[str, Any] | None = None) -> bytes:
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-User": self.config.username,
            "X-Role": self.config.role,
        }
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        request = Request(
            f"{self.config.server.rstrip('/')}{path}",
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                return response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise MdkError(f"HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise MdkError(f"Cannot connect to MMS at {self.config.server}: {exc.reason}") from exc


def load_model_file(file_path: str | Path, tool: str = "auto") -> dict[str, Any]:
    try:
        return adapter_load_model_result(file_path, tool).model
    except AdapterError as exc:
        raise MdkError(str(exc)) from exc


def detect_tool(path: Path, requested: str = "auto") -> str:
    try:
        from .integrations.adapters import select_adapter

        return select_adapter(path, requested).id
    except AdapterError as exc:
        raise MdkError(str(exc)) from exc


def load_json_model(path: Path) -> dict[str, Any]:
    return load_model_file(path, "json")


def load_xmi_model(path: Path, tool: str = "xmi") -> dict[str, Any]:
    return load_model_file(path, tool)


def load_jupyter_model(path: Path) -> dict[str, Any]:
    return load_model_file(path, "jupyter")


def load_matlab_model(path: Path) -> dict[str, Any]:
    return load_model_file(path, "matlab")


def model_from_elements(elements: list[dict[str, Any]], tool: str, path: Path) -> dict[str, Any]:
    from .integrations.adapters import model_from_elements as adapter_model_from_elements

    result = adapter_model_from_elements(elements, tool, str(path))
    if not result.model.get("elements"):
        raise MdkError(f"{tool} file has no sysml_docgen elements: {path}")
    return result.model


def normalize_elements(payload: Any) -> list[dict[str, Any]]:
    from .integrations.adapters import normalize_elements as adapter_normalize_elements

    return adapter_normalize_elements(payload)


def extract_commented_elements(source: str, prefix: str) -> list[dict[str, Any]]:
    from .integrations.adapters import extract_commented_elements as adapter_extract_commented_elements

    return adapter_extract_commented_elements(source, prefix)


def dedupe_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    anonymous: list[dict[str, Any]] = []
    for element in elements:
        element_id = str(element.get("id", "")).strip()
        if element_id:
            by_id[element_id] = element
        else:
            anonymous.append(element)
    return [*by_id.values(), *anonymous]


def write_document(document: dict[str, Any], output_format: str, out_path: str | Path) -> None:
    path = Path(out_path)
    if output_format == "pdf":
        path.write_bytes(base64.b64decode(document["pdf_base64"]))
        return
    if output_format == "docx":
        docx_base64 = document.get("docx_base64")
        if not docx_base64:
            raise MdkError("DOCX 内容不可用，请确认已安装 Quarto 或 Pandoc")
        path.write_bytes(base64.b64decode(docx_base64))
        return
    key = "markdown" if output_format == "markdown" else "html"
    path.write_text(document[key], encoding="utf-8")

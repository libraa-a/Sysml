"""Adapter registry for external engineering tool model exchange."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from ..xmi import parse_xmi_with_report
from .types import AdapterCapabilities, AdapterParseResult, MappingReport


SUPPORTED_TOOLS = {"auto", "json", "xmi", "cameo", "jupyter", "matlab"}


class AdapterError(RuntimeError):
    """Raised when no adapter can parse a tool artifact."""


class ToolAdapter(Protocol):
    id: str
    label: str
    capabilities: AdapterCapabilities

    def matches(self, path: Path, requested: str = "auto") -> bool: ...

    def parse_file(self, path: Path) -> AdapterParseResult: ...

    def parse_content(self, content: Any, filename: str = "") -> AdapterParseResult: ...

    def describe(self) -> dict[str, Any]: ...


class BaseAdapter:
    id = "base"
    label = "Base adapter"
    capabilities = AdapterCapabilities()

    def describe(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, **self.capabilities.to_dict()}

    def matches(self, path: Path, requested: str = "auto") -> bool:
        return requested == self.id

    def parse_file(self, path: Path) -> AdapterParseResult:
        return self.parse_content(path.read_text(encoding="utf-8-sig"), str(path))

    def parse_content(self, content: Any, filename: str = "") -> AdapterParseResult:
        raise NotImplementedError

    def _model(self, elements: list[dict[str, Any]], source_file: str = "", format_name: str = "json") -> dict[str, Any]:
        report = MappingReport(adapter=self.id, imported=len(elements))
        model = {
            "format": format_name,
            "elements": elements,
            "source": {"adapter": self.id, "tool": self.id},
            "mapping_report": report.to_dict(),
        }
        if source_file:
            model["source"]["file"] = source_file
        return model


class JsonAdapter(BaseAdapter):
    id = "json"
    label = "Generic JSON model"
    capabilities = AdapterCapabilities(
        can_read=True,
        can_write=True,
        can_validate=True,
        can_commit=True,
        can_rollback=False,
        formats=("json",),
        supported_extensions=(".json",),
        input_mime_types=("application/json",),
        output_formats=("json",),
        limitations=("Requires SysML DocGen element shape or an elements collection.",),
    )

    def matches(self, path: Path, requested: str = "auto") -> bool:
        return requested == self.id or (requested == "auto" and path.suffix.lower() == ".json")

    def parse_content(self, content: Any, filename: str = "") -> AdapterParseResult:
        payload = json.loads(content) if isinstance(content, str) else content
        elements = normalize_elements(payload)
        report = MappingReport(adapter=self.id, imported=len(elements))
        model = self._model(elements, filename)
        model["mapping_report"] = report.to_dict()
        return AdapterParseResult(model, report)


class XmiAdapter(BaseAdapter):
    id = "xmi"
    label = "Generic XMI"
    capabilities = AdapterCapabilities(
        can_read=True,
        can_write=True,
        can_validate=True,
        can_commit=True,
        can_rollback=False,
        formats=("xmi", "xml"),
        supported_extensions=(".xmi", ".xml"),
        input_mime_types=("application/xml", "text/xml"),
        output_formats=("xmi", "xml", "json"),
        limitations=("Parses a pragmatic UML/XMI subset and preserves unsupported data as tagged values when possible.",),
    )

    def matches(self, path: Path, requested: str = "auto") -> bool:
        return requested == self.id or (requested == "auto" and path.suffix.lower() in {".xmi", ".xml"})

    def parse_content(self, content: Any, filename: str = "") -> AdapterParseResult:
        result = parse_xmi_with_report(str(content), self.id)
        result.model["source"] = {"adapter": self.id, "tool": self.id}
        if filename:
            result.model["source"]["file"] = filename
        result.model["mapping_report"] = result.report.to_dict()
        return result


class CameoAdapter(XmiAdapter):
    id = "cameo"
    label = "Cameo Systems Modeler XMI"
    capabilities = AdapterCapabilities(
        can_read=True,
        can_write=False,
        can_validate=True,
        can_commit=True,
        can_rollback=False,
        formats=("xmi", "xml"),
        vendor="Dassault Systemes",
        supported_extensions=(".xmi", ".xml"),
        input_mime_types=("application/xml", "text/xml"),
        output_formats=("json",),
        limitations=(
            "Native .mdzip parsing is not supported; export XMI from Cameo first.",
            "Some Cameo profiles may be downgraded to attributes or mapping report warnings.",
        ),
    )

    def matches(self, path: Path, requested: str = "auto") -> bool:
        return requested == self.id or (requested == "auto" and path.suffix.lower() in {".xmi", ".xml"})


class JupyterAdapter(BaseAdapter):
    id = "jupyter"
    label = "Jupyter Notebook"
    capabilities = AdapterCapabilities(
        can_read=True,
        can_write=False,
        can_validate=True,
        can_commit=True,
        can_rollback=False,
        formats=("ipynb",),
        vendor="Project Jupyter",
        supported_extensions=(".ipynb",),
        input_mime_types=("application/x-ipynb+json", "application/json"),
        output_formats=("json",),
        limitations=("Only metadata and sysml-docgen comment blocks are imported.",),
    )

    def matches(self, path: Path, requested: str = "auto") -> bool:
        return requested == self.id or (requested == "auto" and path.suffix.lower() == ".ipynb")

    def parse_content(self, content: Any, filename: str = "") -> AdapterParseResult:
        notebook = json.loads(content) if isinstance(content, str) else content
        elements: list[dict[str, Any]] = []
        metadata = notebook.get("metadata", {}).get("sysml_docgen", {}) if isinstance(notebook, dict) else {}
        elements.extend(normalize_elements(metadata))
        for cell in notebook.get("cells", []) if isinstance(notebook, dict) else []:
            cell_metadata = cell.get("metadata", {}).get("sysml_docgen", {})
            elements.extend(normalize_elements(cell_metadata))
            source = "".join(cell.get("source", []))
            elements.extend(extract_commented_elements(source, "#"))
        return model_from_elements(elements, self.id, filename)


class MatlabAdapter(BaseAdapter):
    id = "matlab"
    label = "MATLAB script"
    capabilities = AdapterCapabilities(
        can_read=True,
        can_write=False,
        can_validate=True,
        can_commit=True,
        can_rollback=False,
        formats=("m", "mlx"),
        vendor="MathWorks",
        supported_extensions=(".m", ".mlx"),
        input_mime_types=("text/x-matlab", "text/plain"),
        output_formats=("json",),
        limitations=("Only sysml-docgen comment blocks are imported from MATLAB files.",),
    )

    def matches(self, path: Path, requested: str = "auto") -> bool:
        return requested == self.id or (requested == "auto" and path.suffix.lower() in {".m", ".mlx"})

    def parse_content(self, content: Any, filename: str = "") -> AdapterParseResult:
        return model_from_elements(extract_commented_elements(str(content), "%"), self.id, filename)


ADAPTERS: tuple[ToolAdapter, ...] = (
    JsonAdapter(),
    CameoAdapter(),
    XmiAdapter(),
    JupyterAdapter(),
    MatlabAdapter(),
)


def list_adapters() -> list[dict[str, Any]]:
    return [adapter.describe() for adapter in ADAPTERS]


def get_adapter(adapter_id: str) -> ToolAdapter:
    for adapter in ADAPTERS:
        if adapter.id == adapter_id:
            return adapter
    supported = ", ".join(sorted(SUPPORTED_TOOLS))
    raise AdapterError(f"tool must be one of: {supported}")


def select_adapter(path: Path, requested: str = "auto") -> ToolAdapter:
    requested = requested.lower()
    if requested not in SUPPORTED_TOOLS:
        supported = ", ".join(sorted(SUPPORTED_TOOLS))
        raise AdapterError(f"tool must be one of: {supported}")
    if requested != "auto":
        if path.suffix.lower() == ".mdzip":
            raise AdapterError("Cameo .mdzip is proprietary; export XMI from Cameo before pushing to MMS.")
        return get_adapter(requested)
    if path.suffix.lower() == ".mdzip":
        raise AdapterError("Cameo .mdzip is proprietary; export XMI from Cameo before pushing to MMS.")
    for adapter in ADAPTERS:
        if adapter.matches(path, requested):
            return adapter
    raise AdapterError(f"Cannot detect MDK adapter for file: {path.name}")


def load_model_result(file_path: str | Path, tool: str = "auto") -> AdapterParseResult:
    path = Path(file_path)
    if not path.exists():
        raise AdapterError(f"Model file does not exist: {path}")
    adapter = select_adapter(path, tool)
    return adapter.parse_file(path)


def load_model_file(file_path: str | Path, tool: str = "auto") -> dict[str, Any]:
    return load_model_result(file_path, tool).model


def parse_content(content: Any, filename: str = "", tool: str = "auto") -> AdapterParseResult:
    if tool and tool != "auto":
        adapter = get_adapter(tool.lower())
    elif filename:
        adapter = select_adapter(Path(filename), "auto")
    else:
        adapter = get_adapter("json")
    return adapter.parse_content(content, filename)


def normalize_elements(payload: Any) -> list[dict[str, Any]]:
    if not payload:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("elements"), list):
            return [item for item in payload["elements"] if isinstance(item, dict)]
        if isinstance(payload.get("elements"), dict):
            return [item for item in payload["elements"].values() if isinstance(item, dict)]
        if isinstance(payload.get("element"), dict):
            return [payload["element"]]
        if {"id", "type"} <= set(payload):
            return [payload]
    return []


def extract_commented_elements(source: str, prefix: str) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    block_lines: list[str] = []
    in_block = False
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line.startswith(prefix):
            continue
        content = line[len(prefix) :].strip()
        if content == "sysml-docgen:begin":
            in_block = True
            block_lines = []
            continue
        if content == "sysml-docgen:end":
            in_block = False
            elements.extend(normalize_elements(json.loads("\n".join(block_lines))))
            continue
        if in_block:
            block_lines.append(content)
            continue
        if content.startswith("sysml-docgen:element"):
            raw_json = content.removeprefix("sysml-docgen:element").strip()
            elements.extend(normalize_elements(json.loads(raw_json)))
        if content.startswith("sysml-docgen:elements"):
            raw_json = content.removeprefix("sysml-docgen:elements").strip()
            elements.extend(normalize_elements(json.loads(raw_json)))
    return elements


def model_from_elements(elements: list[dict[str, Any]], tool: str, source_file: str = "") -> AdapterParseResult:
    deduped = dedupe_elements(elements)
    report = MappingReport(adapter=tool, imported=len(deduped))
    if not deduped:
        report.warnings.append(f"{tool} file has no sysml_docgen elements")
    model = {
        "format": "json",
        "elements": deduped,
        "source": {"adapter": tool, "tool": tool},
        "mapping_report": report.to_dict(),
    }
    if source_file:
        model["source"]["file"] = source_file
    return AdapterParseResult(model, report)


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

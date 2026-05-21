"""Shared contracts for external tool adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class AdapterCapabilities:
    can_read: bool = True
    can_write: bool = False
    can_validate: bool = True
    can_commit: bool = True
    can_rollback: bool = False
    formats: tuple[str, ...] = ()
    vendor: str = "SysML DocGen"
    version: str = "1.0.0"
    supported_extensions: tuple[str, ...] = ()
    input_mime_types: tuple[str, ...] = ()
    output_formats: tuple[str, ...] = ()
    schema_version: str = "mdk-adapter/v1"
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "formats",
            "supported_extensions",
            "input_mime_types",
            "output_formats",
            "limitations",
        ):
            payload[key] = list(payload[key])
        return payload


@dataclass(slots=True)
class MappingReport:
    adapter: str
    imported: int = 0
    skipped: list[dict[str, Any]] = field(default_factory=list)
    converted: list[dict[str, Any]] = field(default_factory=list)
    downgraded: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AdapterParseResult:
    model: dict[str, Any]
    report: MappingReport

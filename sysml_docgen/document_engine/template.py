"""Template rendering helpers extracted from docgen."""

from __future__ import annotations

import json
import re
from typing import Any

from .traceability import (
    build_traceability,
    elements_by_type,
    render_model_summary_markdown,
    render_traceability_markdown,
    render_validation_markdown,
)
from ..metamodel import TYPE_LABELS

Element = dict[str, Any]
TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z]+):([^}]+)\s*\}\}")


def get_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return ""
    return current


def resolve_element_token(elements: dict[str, Element], expression: str) -> str:
    if "." not in expression:
        element = elements.get(expression.strip())
        return str(element.get("name", "")) if element else ""

    element_id, path = expression.split(".", 1)
    element = elements.get(element_id.strip())
    if not element:
        return ""
    value = get_path(element, path.strip())
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def render_template(template: str, elements: dict[str, Element]) -> str:
    """Render a compact DocGen-like template into Markdown."""

    def replace(match: re.Match[str]) -> str:
        token_type = match.group(1).lower()
        expression = match.group(2).strip()
        if token_type == "element":
            return resolve_element_token(elements, expression)
        if token_type == "table":
            return render_markdown_table(elements, expression)
        if token_type == "trace":
            return render_traceability_markdown(elements)
        if token_type == "model":
            return render_model_summary_markdown(elements)
        if token_type == "validation":
            return render_validation_markdown(elements)
        return match.group(0)

    return TOKEN_RE.sub(replace, template)


def render_markdown_table(elements: dict[str, Element], table_name: str) -> str:
    name = table_name.lower()
    if name in {"requirements", "requirement", "req"}:
        return render_requirements_table(elements)
    if name in {"blocks", "block", "structure"}:
        return render_blocks_table(elements)
    if name in {"tests", "testcases", "verification"}:
        return render_tests_table(elements)
    if name in {"interfaces", "ports", "interface"}:
        return render_interfaces_table(elements)
    if name in {"constraints", "constraint"}:
        return render_constraints_table(elements)
    if name in {"states", "state"}:
        return render_states_table(elements)
    return ""


def render_requirements_table(elements: dict[str, Element]) -> str:
    rows = ["| ID | Name | Requirement Text | Verification |", "| --- | --- | --- | --- |"]
    for item in elements_by_type(elements, "Requirement"):
        rows.append(
            "| {id} | {name} | {text} | {verification} |".format(
                id=item.get("id", ""),
                name=item.get("name", ""),
                text=item.get("attributes", {}).get("text", item.get("description", "")),
                verification=item.get("attributes", {}).get("verification", ""),
            )
        )
    return "\n".join(rows)


def render_blocks_table(elements: dict[str, Element]) -> str:
    rows = ["| ID | Name | Owner | Description |", "| --- | --- | --- | --- |"]
    for item in elements_by_type(elements, "Block"):
        rows.append(
            f"| {item.get('id', '')} | {item.get('name', '')} | "
            f"{item.get('owner', '')} | {item.get('description', '')} |"
        )
    return "\n".join(rows)


def render_tests_table(elements: dict[str, Element]) -> str:
    rows = ["| ID | Name | Method | Criterion |", "| --- | --- | --- | --- |"]
    for item in elements_by_type(elements, "TestCase"):
        rows.append(
            f"| {item.get('id', '')} | {item.get('name', '')} | "
            f"{item.get('attributes', {}).get('method', '')} | "
            f"{item.get('attributes', {}).get('criterion', item.get('description', ''))} |"
        )
    return "\n".join(rows)


def render_interfaces_table(elements: dict[str, Element]) -> str:
    rows = ["| ID | Type | Name | Direction/Protocol | Description |", "| --- | --- | --- | --- | --- |"]
    for item in elements_by_type(elements, "Interface") + elements_by_type(elements, "Port"):
        attrs = item.get("attributes", {})
        protocol = attrs.get("protocol") or attrs.get("direction") or attrs.get("interface", "")
        rows.append(
            f"| {item.get('id', '')} | {TYPE_LABELS.get(item.get('type', ''), item.get('type', ''))} | "
            f"{item.get('name', '')} | {protocol} | {item.get('description', '')} |"
        )
    return "\n".join(rows)


def render_constraints_table(elements: dict[str, Element]) -> str:
    rows = ["| ID | Name | Expression | Description |", "| --- | --- | --- | --- |"]
    for item in elements_by_type(elements, "Constraint"):
        rows.append(
            f"| {item.get('id', '')} | {item.get('name', '')} | "
            f"{item.get('attributes', {}).get('expression', '')} | {item.get('description', '')} |"
        )
    return "\n".join(rows)


def render_states_table(elements: dict[str, Element]) -> str:
    rows = ["| ID | State | Description |", "| --- | --- | --- |"]
    for item in elements_by_type(elements, "State"):
        rows.append(f"| {item.get('id', '')} | {item.get('name', '')} | {item.get('description', '')} |")
    return "\n".join(rows)


def default_document_template(project: dict[str, Any], branch_name: str) -> str:
    return f"""# {project.get("name", "SysML Model Document")}

## 1. Document Overview

This document is generated automatically from the SysML model repository. The source branch is `{branch_name}`.

## 2. Model Summary

{{{{model:summary}}}}

## 3. Requirements Baseline

{{{{table:requirements}}}}

## 4. System Structure

{{{{table:blocks}}}}

## 5. Interfaces and Ports

{{{{table:interfaces}}}}

## 6. Constraints and Verification

{{{{table:constraints}}}}

{{{{table:tests}}}}

## 7. Traceability Matrix

{{{{trace:matrix}}}}

## 8. Validation

{{{{validation:issues}}}}
"""

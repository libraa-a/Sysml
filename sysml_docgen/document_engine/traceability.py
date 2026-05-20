"""Traceability helpers extracted from docgen."""

from __future__ import annotations

import copy
from typing import Any

from ..metamodel import TYPE_LABELS, validate_repository

Element = dict[str, Any]


def elements_by_type(elements: dict[str, Element], element_type: str) -> list[Element]:
    return sorted(
        [copy.deepcopy(item) for item in elements.values() if item.get("type") == element_type],
        key=lambda item: item.get("id", ""),
    )


def build_traceability(elements: dict[str, Element]) -> list[dict[str, Any]]:
    requirements = elements_by_type(elements, "Requirement")
    rows: list[dict[str, Any]] = []
    for requirement in requirements:
        requirement_id = str(requirement.get("id", ""))
        satisfy_ids = trace_ids_for_requirement(elements, requirement, "satisfy")
        verify_ids = trace_ids_for_requirement(elements, requirement, "verify")
        refine_ids = trace_ids_for_requirement(elements, requirement, "refine")
        constrain_ids = trace_ids_for_requirement(elements, requirement, "constrain")
        satisfied_refs = refs_from_ids(elements, satisfy_ids, exclude_id=requirement_id)
        verified_refs = refs_from_ids(elements, verify_ids, exclude_id=requirement_id)
        refined_refs = refs_from_ids(elements, refine_ids, exclude_id=requirement_id)
        constrained_refs = refs_from_ids(elements, constrain_ids, exclude_id=requirement_id)
        rows.append(
            {
                "requirement": compact_ref(requirement),
                "satisfied_by": satisfied_refs,
                "verified_by": verified_refs,
                "refined_by": refined_refs,
                "constrained_by": constrained_refs,
                "status": trace_status(satisfied_refs, verified_refs),
            }
        )
    return rows


def trace_ids_for_requirement(elements: dict[str, Element], requirement: Element, relation_type: str) -> list[str]:
    requirement_id = str(requirement.get("id", ""))
    return unique_ids(
        [
            *related_targets(requirement, relation_type),
            *incoming_sources(elements, requirement_id, relation_type),
        ]
    )


def related_targets(element: Element, relation_type: str) -> list[str]:
    return [
        relation.get("target", "")
        for relation in element.get("relations", [])
        if relation.get("type") == relation_type and relation.get("target")
    ]


def incoming_sources(elements: dict[str, Element], target_id: str, relation_type: str) -> list[str]:
    sources = []
    for element_id, element in elements.items():
        for relation in element.get("relations", []):
            if relation.get("type") == relation_type and relation.get("target") == target_id:
                sources.append(element_id)
    return sources


def unique_ids(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def refs_from_ids(elements: dict[str, Element], element_ids: list[str], exclude_id: str = "") -> list[dict[str, str]]:
    return [
        compact_ref(elements[element_id])
        for element_id in element_ids
        if element_id in elements and element_id != exclude_id
    ]


def compact_ref(element: Element) -> dict[str, str]:
    return {
        "id": str(element.get("id", "")),
        "name": str(element.get("name", "")),
        "type": str(element.get("type", "")),
    }


def trace_status(satisfied_refs: list[dict[str, str]], verified_refs: list[dict[str, str]]) -> str:
    if satisfied_refs and verified_refs:
        return "closed"
    if satisfied_refs or verified_refs:
        return "partial"
    return "open"


def render_model_summary_markdown(elements: dict[str, Element]) -> str:
    counts: dict[str, int] = {}
    for element in elements.values():
        counts[element.get("type", "Unknown")] = counts.get(element.get("type", "Unknown"), 0) + 1
    rows = [
        f"Current model contains {len(elements)} SysML elements. The following summary is generated from the MMS repository.",
        "",
        "| Type | Count |",
        "| --- | ---: |",
    ]
    for key in sorted(counts):
        rows.append(f"| {TYPE_LABELS.get(key, key)} | {counts[key]} |")
    return "\n".join(rows)


def render_traceability_markdown(elements: dict[str, Element]) -> str:
    rows = ["| Requirement | Satisfied By | Verified By | Refined By | Constrained By | Status |", "| --- | --- | --- | --- | --- | --- |"]
    for row in build_traceability(elements):
        req = row["requirement"]
        satisfied = ", ".join(f"{item['id']} {item['name']}" for item in row["satisfied_by"]) or "-"
        verified = ", ".join(f"{item['id']} {item['name']}" for item in row["verified_by"]) or "-"
        refined = ", ".join(f"{item['id']} {item['name']}" for item in row["refined_by"]) or "-"
        constrained = ", ".join(f"{item['id']} {item['name']}" for item in row["constrained_by"]) or "-"
        rows.append(
            f"| {req['id']} {req['name']} | {satisfied} | {verified} | {refined} | {constrained} | {row['status']} |"
        )
    return "\n".join(rows)


def render_validation_markdown(elements: dict[str, Element]) -> str:
    validation = validate_repository(elements)
    rows = ["| Severity | Element | Issue |", "| --- | --- | --- |"]
    for item in validation["issues"][:50]:
        rows.append(f"| {item['severity']} | {item['element_id']} | {item['message']} |")
    if len(rows) == 2:
        rows.append("| info | - | No semantic validation issues found |")
    return "\n".join(rows)

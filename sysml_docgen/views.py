"""View helpers for treating SysML View elements as first-class scopes."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from .document_engine.traceability import (
    render_model_summary_markdown,
    render_traceability_markdown,
    render_validation_markdown,
)
from .metamodel import TYPE_LABELS, build_diagram


Element = dict[str, Any]
VIEW_TEMPLATE_TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}")
DEFAULT_VIEW_TEMPLATE_NAME = "summary-trace-validation"


def list_view_elements(elements: dict[str, Element]) -> list[Element]:
    """Return all View elements in deterministic order."""
    return sorted(
        [copy.deepcopy(element) for element in elements.values() if element.get("type") == "View"],
        key=lambda element: element.get("id", ""),
    )


def view_payload(elements: dict[str, Element], view_id: str) -> dict[str, Any]:
    """Build a public payload for a single View and its resolved element scope."""
    view = elements.get(view_id)
    if not view or view.get("type") != "View":
        raise KeyError(view_id)
    viewpoint = resolve_viewpoint(elements, view)
    scope = _resolve_view_scope_details(elements, view, viewpoint)
    return {
        "view": copy.deepcopy(view),
        "viewpoint": copy.deepcopy(viewpoint) if viewpoint else None,
        "view_query": copy.deepcopy(scope["view_query"]),
        "viewpoint_default_query": copy.deepcopy(scope["viewpoint_default_query"]),
        "effective_query": copy.deepcopy(scope["effective_query"]),
        "root_element_ids": list(scope["root_element_ids"]),
        "manual_element_ids": list(scope["manual_element_ids"]),
        "query_element_ids": list(scope["query_element_ids"]),
        "automatic_element_ids": list(scope["automatic_element_ids"]),
        "overlap_element_ids": list(scope["overlap_element_ids"]),
        "content_element_ids": list(scope["content_element_ids"]),
        "content_count": len(scope["content_element_ids"]),
        "content_summary": view_scope_summary(scope["content_map"]),
        "manual_elements": list(scope["manual_elements"]),
        "query_elements": list(scope["query_elements"]),
        "automatic_elements": list(scope["automatic_elements"]),
        "content_elements": list(scope["content_elements"]),
        "elements": list(scope["elements"]),
        "element_count": len(scope["elements"]),
        "element_ids": list(scope["element_ids"]),
        "summary": view_scope_summary(scope["element_map"]),
        "scope_breakdown": {
            "manual": len(scope["manual_element_ids"]),
            "query": len(scope["query_element_ids"]),
            "automatic": len(scope["automatic_element_ids"]),
            "overlap": len(scope["overlap_element_ids"]),
            "content": len(scope["content_element_ids"]),
        },
    }


def resolve_view_scope(elements: dict[str, Element], view: Element) -> dict[str, Element]:
    """Resolve elements selected by a View's manual bindings and query rules."""
    viewpoint = resolve_viewpoint(elements, view)
    details = _resolve_view_scope_details(elements, view, viewpoint)
    return details["element_map"]


def build_view_diagram(elements: dict[str, Element], view_id: str) -> dict[str, Any]:
    """Build a diagram limited to the elements selected by a View."""
    payload = view_payload(elements, view_id)
    diagram = build_diagram({item["id"]: item for item in payload["elements"]}, "views")
    existing_edges = {
        (edge.get("source"), edge.get("target"), edge.get("type"))
        for edge in diagram.get("edges", [])
    }
    for element_id in payload["content_element_ids"]:
        if element_id == view_id:
            continue
        edge_key = (view_id, element_id, "include")
        if edge_key in existing_edges:
            continue
        diagram["edges"].append(
            {
                "source": view_id,
                "target": element_id,
                "type": "include",
                "label": "Include",
            }
        )
        existing_edges.add(edge_key)
    viewpoint = payload.get("viewpoint")
    if viewpoint:
        edge_key = (view_id, viewpoint.get("id"), "conform")
        if edge_key not in existing_edges:
            diagram["edges"].append(
                {
                    "source": view_id,
                    "target": viewpoint.get("id"),
                    "type": "conform",
                    "label": "Conform",
                }
            )
    diagram["view"] = payload["view"]
    diagram["viewpoint"] = viewpoint
    diagram["label"] = payload["view"].get("name") or payload["view"].get("id", view_id)
    return diagram


def render_view_markdown(elements: dict[str, Element], view_id: str) -> str:
    """Render a View as a standalone Markdown section."""
    payload = view_payload(elements, view_id)
    viewpoint = payload.get("viewpoint")
    view = payload["view"]
    content = {element["id"]: element for element in payload["content_elements"]}

    template = (viewpoint or {}).get("attributes", {}).get("document_template")
    if isinstance(template, str) and template.strip() and template.strip() != DEFAULT_VIEW_TEMPLATE_NAME:
        return render_view_template(template, payload, content)

    return _render_default_view_markdown(payload, content)


def render_view_template(template: str, payload: dict[str, Any], scoped: dict[str, Element]) -> str:
    """Render a Viewpoint-owned markdown template for a resolved View payload."""

    def replace(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        value = _resolve_view_template_token(token, payload, scoped)
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value or "")

    return VIEW_TEMPLATE_TOKEN_RE.sub(replace, template)


def validate_view_against_viewpoint(elements: dict[str, Element], view: Element) -> list[dict[str, Any]]:
    """Validate that a View's resolved scope conforms to its linked Viewpoint rules."""
    view_id = str(view.get("id", ""))
    declared_viewpoint_id = _declared_viewpoint_id(view)
    viewpoint = resolve_viewpoint(elements, view)
    if declared_viewpoint_id and not viewpoint:
        return [
            _issue(
                "warning",
                view_id,
                f"View references missing Viewpoint {declared_viewpoint_id}",
            )
        ]
    if not viewpoint:
        return []

    issues: list[dict[str, Any]] = []
    viewpoint_id = str(viewpoint.get("id", ""))
    attrs = viewpoint.get("attributes", {})
    allowed_types = _as_set(attrs.get("allowed_types"))
    required_types = _as_set(attrs.get("required_types"))
    allowed_relations = _as_set(attrs.get("allowed_relations"))

    scoped = resolve_view_scope(elements, view)
    content = {
        element_id: element
        for element_id, element in scoped.items()
        if element.get("type") not in {"View", "Viewpoint"}
    }

    if allowed_types:
        for element in content.values():
            element_type = str(element.get("type", ""))
            if element_type not in allowed_types:
                issues.append(
                    _issue(
                        "warning",
                        view_id,
                        f"Viewpoint {viewpoint_id} does not allow {element_type} element {element.get('id', '')}",
                    )
                )

    for required_type in sorted(required_types):
        if not any(element.get("type") == required_type for element in content.values()):
            issues.append(
                _issue(
                    "warning",
                    view_id,
                    f"Viewpoint {viewpoint_id} requires at least one {required_type} element in the View scope",
                )
            )

    if allowed_relations:
        content_ids = set(content)
        for source in content.values():
            for relation in source.get("relations", []):
                target_id = str(relation.get("target", ""))
                relation_type = str(relation.get("type", ""))
                if target_id in content_ids and relation_type not in allowed_relations:
                    issues.append(
                        _issue(
                            "warning",
                            view_id,
                            f"Viewpoint {viewpoint_id} does not allow relation {relation_type} from {source.get('id', '')} to {target_id}",
                        )
                    )
    return issues


def _render_default_view_markdown(payload: dict[str, Any], scoped: dict[str, Element]) -> str:
    view = payload["view"]
    viewpoint_element = payload.get("viewpoint")
    attrs = view.get("attributes", {})
    view_id = str(view.get("id", "view"))
    title = attrs.get("doc_section_title") or view.get("name") or view_id
    viewpoint = (
        (viewpoint_element or {}).get("name")
        or attrs.get("viewpoint")
        or attrs.get("viewpoint_id")
        or "General"
    )

    rows = [
        f"## {title}",
        "",
        f"View ID: `{view.get('id', view_id)}`",
        "",
        f"Viewpoint: {viewpoint}",
        "",
        view.get("description", ""),
        "",
        "### View Scope",
        "",
        _render_scope_table(scoped),
    ]
    rows.extend(["", "### View Summary", "", render_model_summary_markdown(scoped), "", "### View Traceability", ""])
    rows.append(render_traceability_markdown(scoped))
    rows.extend(["", "### View Validation", "", render_validation_markdown(scoped)])
    return "\n".join(line for line in rows if line is not None)


def _render_scope_table(scoped: dict[str, Element]) -> str:
    rows = ["| Type | ID | Name |", "| --- | --- | --- |"]
    for element in scoped.values():
        rows.append(
            f"| {TYPE_LABELS.get(element.get('type', ''), element.get('type', ''))} "
            f"| {element.get('id', '')} | {element.get('name', '')} |"
        )
    return "\n".join(rows)


def _resolve_view_template_token(token: str, payload: dict[str, Any], scoped: dict[str, Element]) -> Any:
    view = payload.get("view", {})
    viewpoint = payload.get("viewpoint") or {}
    token_map = {
        "view.id": view.get("id", ""),
        "view.name": view.get("name", ""),
        "view.description": view.get("description", ""),
        "view.owner": view.get("owner", ""),
        "viewpoint.id": viewpoint.get("id", ""),
        "viewpoint.name": viewpoint.get("name", ""),
        "viewpoint.description": viewpoint.get("description", ""),
        "viewpoint.purpose": viewpoint.get("attributes", {}).get("purpose", ""),
        "view.scope": _render_scope_table(scoped),
        "view.manual_scope": _render_scope_table(_element_map(payload.get("content_elements", []), payload.get("manual_element_ids", []))),
        "view.automatic_scope": _render_scope_table(_element_map(payload.get("content_elements", []), payload.get("automatic_element_ids", []))),
        "view.content_scope": _render_scope_table(_element_map(payload.get("content_elements", []), payload.get("content_element_ids", []))),
        "view.summary": render_model_summary_markdown(scoped),
        "view.traceability": render_traceability_markdown(scoped),
        "view.validation": render_validation_markdown(scoped),
        "view.manual_count": payload.get("scope_breakdown", {}).get("manual", 0),
        "view.automatic_count": payload.get("scope_breakdown", {}).get("automatic", 0),
        "view.content_count": payload.get("scope_breakdown", {}).get("content", 0),
        "view.view_query": payload.get("view_query", {}),
        "view.viewpoint_default_query": payload.get("viewpoint_default_query", {}),
        "view.effective_query": payload.get("effective_query", {}),
    }
    if token in token_map:
        return token_map[token]
    if token.startswith("view.attributes."):
        return _get_path(view.get("attributes", {}), token.removeprefix("view.attributes."))
    if token.startswith("viewpoint.attributes."):
        return _get_path(viewpoint.get("attributes", {}), token.removeprefix("viewpoint.attributes."))
    return "{{" + token + "}}"


def _declared_viewpoint_id(view: Element) -> str:
    attrs = view.get("attributes", {})
    viewpoint_id = str(attrs.get("viewpoint_id") or "").strip()
    for relation in view.get("relations", []):
        if relation.get("type") == "conform" and relation.get("target"):
            viewpoint_id = str(relation.get("target", "")).strip()
            break
    return viewpoint_id


def _get_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return ""
    return current


def _issue(severity: str, element_id: str, message: str) -> dict[str, str]:
    return {"severity": severity, "element_id": element_id or "-", "message": message}


def _resolve_view_scope_details(
    elements: dict[str, Element],
    view: Element,
    viewpoint: Element | None,
) -> dict[str, Any]:
    view_id = str(view.get("id", ""))
    viewpoint_id = str((viewpoint or {}).get("id", ""))
    root_ids = [view_id]
    if viewpoint_id:
        root_ids.append(viewpoint_id)

    manual_ids = _dedupe_ids(
        [
            *_list_attribute(view, "included_elements"),
            *_list_attribute(view, "elements"),
            *_include_relation_targets(view),
        ]
    )

    query = _effective_query(view, viewpoint)
    if not isinstance(query, dict):
        query = {}
    viewpoint_default_query = {}
    if viewpoint:
        raw_query = viewpoint.get("attributes", {}).get("default_query", {})
        if isinstance(raw_query, dict):
            viewpoint_default_query = raw_query
    view_query = view.get("attributes", {}).get("query", {})
    if not isinstance(view_query, dict):
        view_query = {}
    effective_query = _merge_query(viewpoint_default_query, view_query)

    manual_content_ids = _filter_scope_content_ids(elements, manual_ids)
    query_ids = _expand_by_depth(
        elements,
        _query_matches(elements, effective_query),
        _relation_depth(effective_query),
        _as_set(effective_query.get("relations")) if isinstance(effective_query, dict) else set(),
    )
    query_content_ids = _filter_scope_content_ids(elements, query_ids)
    query_set = set(query_content_ids)
    manual_set = set(manual_content_ids)
    automatic_content_ids = _filter_scope_content_ids(
        elements,
        [element_id for element_id in query_content_ids if element_id not in manual_set],
    )
    content_ids = _dedupe_ids([*manual_content_ids, *automatic_content_ids])
    element_ids = _dedupe_ids([*root_ids, *content_ids])

    element_map: dict[str, Element] = {}
    for element_id in element_ids:
        if element_id in elements:
            element_map[element_id] = copy.deepcopy(elements[element_id])

    content_map: dict[str, Element] = {}
    for element_id in content_ids:
        if element_id in elements:
            content_map[element_id] = copy.deepcopy(elements[element_id])

    return {
        "root_element_ids": root_ids,
        "manual_element_ids": manual_content_ids,
        "query_element_ids": query_content_ids,
        "automatic_element_ids": automatic_content_ids,
        "overlap_element_ids": [element_id for element_id in manual_content_ids if element_id in query_set],
        "content_element_ids": content_ids,
        "manual_elements": [element_map[element_id] for element_id in manual_content_ids if element_id in element_map],
        "query_elements": [content_map[element_id] for element_id in query_content_ids if element_id in content_map],
        "automatic_elements": [content_map[element_id] for element_id in automatic_content_ids if element_id in content_map],
        "content_elements": [content_map[element_id] for element_id in content_ids if element_id in content_map],
        "content_map": content_map,
        "element_ids": element_ids,
        "elements": [element_map[element_id] for element_id in element_ids if element_id in element_map],
        "element_map": element_map,
        "view_query": view_query,
        "viewpoint_default_query": viewpoint_default_query,
        "effective_query": effective_query,
    }


def view_scope_summary(elements: dict[str, Element]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for element in elements.values():
        element_type = str(element.get("type", "Unknown"))
        counts[element_type] = counts.get(element_type, 0) + 1
    return counts


def resolve_viewpoint(elements: dict[str, Element], view: Element) -> Element | None:
    """Resolve the Viewpoint element linked by attributes or conform relation."""
    attrs = view.get("attributes", {})
    viewpoint_id = str(attrs.get("viewpoint_id") or "").strip()
    if not viewpoint_id:
        viewpoint_id = str(attrs.get("viewpoint") or "").strip()
    for relation in view.get("relations", []):
        if relation.get("type") == "conform" and relation.get("target"):
            viewpoint_id = str(relation.get("target", "")).strip()
            break
    viewpoint = elements.get(viewpoint_id)
    if viewpoint and viewpoint.get("type") == "Viewpoint":
        return viewpoint
    return None


def _effective_query(view: Element, viewpoint: Element | None) -> dict[str, Any]:
    view_query = view.get("attributes", {}).get("query", {})
    if not isinstance(view_query, dict):
        view_query = {}
    viewpoint_query = {}
    if viewpoint:
        raw = viewpoint.get("attributes", {}).get("default_query", {})
        if isinstance(raw, dict):
            viewpoint_query = raw
    return _merge_query(viewpoint_query, view_query)


def _merge_query(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if value in (None, "", []):
            continue
        merged[key] = value
    return merged


def _list_attribute(view: Element, name: str) -> list[str]:
    value = view.get("attributes", {}).get(name, [])
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _include_relation_targets(view: Element) -> list[str]:
    return [
        str(relation.get("target", "")).strip()
        for relation in view.get("relations", [])
        if relation.get("type") == "include" and relation.get("target")
    ]


def _query_matches(elements: dict[str, Element], query: dict[str, Any]) -> list[str]:
    requested_types = _as_set(query.get("types"))
    requested_owners = _as_set(query.get("owners"))
    text = str(query.get("text") or query.get("q") or "").strip().lower()
    if not requested_types and not requested_owners and not text:
        return []

    matches: list[str] = []
    for element_id, element in elements.items():
        if requested_types and element.get("type") not in requested_types:
            continue
        if requested_owners and element.get("owner") not in requested_owners:
            continue
        searchable = " ".join(
            [
                str(element.get("id", "")),
                str(element.get("name", "")),
                str(element.get("description", "")),
                str(element.get("owner", "")),
                str(element.get("attributes", "")),
            ]
        ).lower()
        if text and text not in searchable:
            continue
        matches.append(element_id)
    return matches


def _expand_by_depth(
    elements: dict[str, Element],
    selected_ids: list[str],
    depth: int,
    relation_filter: set[str] | None = None,
) -> list[str]:
    selected = [element_id for element_id in selected_ids if element_id]
    seen = set(selected)
    frontier = list(selected)
    relation_filter = relation_filter or set()
    for _ in range(depth):
        next_frontier: list[str] = []
        for element_id in frontier:
            element = elements.get(element_id)
            if not element:
                continue
            for relation in element.get("relations", []):
                if relation_filter and relation.get("type") not in relation_filter:
                    continue
                target = str(relation.get("target", "")).strip()
                if target and target not in seen:
                    seen.add(target)
                    selected.append(target)
                    next_frontier.append(target)
            for source_id, source in elements.items():
                if source_id in seen:
                    continue
                if any(
                    relation.get("target") == element_id
                    and (not relation_filter or relation.get("type") in relation_filter)
                    for relation in source.get("relations", [])
                ):
                    seen.add(source_id)
                    selected.append(source_id)
                    next_frontier.append(source_id)
        frontier = next_frontier
    return selected


def _relation_depth(query: Any) -> int:
    if not isinstance(query, dict):
        return 0
    try:
        return max(0, min(3, int(query.get("relation_depth", 0))))
    except (TypeError, ValueError):
        return 0


def _as_set(value: Any) -> set[str]:
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


def _dedupe_ids(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _filter_scope_content_ids(elements: dict[str, Element], element_ids: list[str]) -> list[str]:
    content: list[str] = []
    for element_id in _dedupe_ids(element_ids):
        element = elements.get(element_id)
        if not element:
            continue
        if element.get("type") in {"View", "Viewpoint"}:
            continue
        content.append(element_id)
    return content


def _element_map(elements: list[Element], element_ids: list[str]) -> dict[str, Element]:
    lookup = {element.get("id", ""): element for element in elements if element.get("id")}
    return {element_id: lookup[element_id] for element_id in element_ids if element_id in lookup}

"""Minimal XMI import/export helpers for the course-design MMS prototype."""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from .metamodel import TYPE_PREFIX, default_stereotype
from .integrations.types import AdapterParseResult, MappingReport


XMI_NS = "http://www.omg.org/spec/XMI/20131001"
UML_NS = "http://www.omg.org/spec/UML/20131001"

ET.register_namespace("xmi", XMI_NS)
ET.register_namespace("uml", UML_NS)


TYPE_TO_UML = {
    "Requirement": "uml:Class",
    "Block": "uml:Class",
    "Activity": "uml:Activity",
    "Interface": "uml:Interface",
    "Port": "uml:Port",
    "Constraint": "uml:Constraint",
    "State": "uml:State",
    "TestCase": "uml:Class",
    "View": "uml:Class",
}

UML_TO_TYPE = {
    "requirement": "Requirement",
    "block": "Block",
    "class": "Block",
    "activity": "Activity",
    "interface": "Interface",
    "interfaceblock": "Interface",
    "port": "Port",
    "proxyport": "Port",
    "fullport": "Port",
    "constraint": "Constraint",
    "constraintblock": "Constraint",
    "state": "State",
    "testcase": "TestCase",
    "test_case": "TestCase",
    "view": "View",
}


def elements_to_xmi(export_payload: dict[str, Any]) -> str:
    """Serialize repository elements into a compact, tool-friendly XMI document."""

    project = export_payload.get("project", {})
    root = ET.Element(_qname(XMI_NS, "XMI"))
    model = ET.SubElement(
        root,
        _qname(UML_NS, "Model"),
        {
            _qname(XMI_NS, "id"): project.get("id", "sysml-model"),
            "name": project.get("name", "SysML Model"),
        },
    )

    elements = export_payload.get("elements", {})
    for element in elements.values():
        element_type = element.get("type", "Block")
        attrs = {
            _qname(XMI_NS, "type"): TYPE_TO_UML.get(element_type, "uml:Class"),
            _qname(XMI_NS, "id"): element.get("id", ""),
            "name": element.get("name", element.get("id", "")),
            "sysmlType": element_type,
            "stereotype": element.get("stereotype", default_stereotype(element_type)),
        }
        packaged = ET.SubElement(model, "packagedElement", attrs)
        if element.get("description"):
            ET.SubElement(packaged, "ownedComment", {"body": str(element.get("description", ""))})
        if element.get("owner"):
            ET.SubElement(packaged, "taggedValue", {"name": "owner", "value": str(element.get("owner", ""))})
        for key, value in sorted(element.get("attributes", {}).items()):
            ET.SubElement(packaged, "taggedValue", {"name": str(key), "value": str(value)})

    relation_index = 1
    for source in elements.values():
        for relation in source.get("relations", []):
            relation_type = str(relation.get("type", "dependency"))
            target = str(relation.get("target", ""))
            if not target:
                continue
            ET.SubElement(
                model,
                "packagedElement",
                {
                    _qname(XMI_NS, "type"): "uml:Dependency",
                    _qname(XMI_NS, "id"): f"REL-{relation_index:04d}",
                    "name": relation_type,
                    "client": str(source.get("id", "")),
                    "supplier": target,
                    "sysmlRelation": relation_type,
                },
            )
            relation_index += 1

    return _xml_declaration(ET.tostring(root, encoding="unicode"))


def parse_xmi_elements(xmi_text: str) -> list[dict[str, Any]]:
    """Parse a pragmatic subset of XMI into the repository element shape."""

    return parse_xmi_with_report(xmi_text).model["elements"]


def parse_xmi_with_report(xmi_text: str, adapter: str = "xmi") -> AdapterParseResult:
    """Parse XMI and explain how source nodes map into repository elements."""

    root = ET.fromstring(xmi_text)
    applied_stereotypes = _applied_stereotypes(root)
    elements: dict[str, dict[str, Any]] = {}
    pending_relations: list[tuple[str, str, str]] = []
    generated_counts: dict[str, int] = {}
    report = MappingReport(adapter=adapter)

    for node in root.iter():
        xmi_type = _attr(node, "type")
        tag = _local_name(node.tag).lower()
        if not xmi_type and tag not in {"packagedelement", "ownedattribute", "ownedport"}:
            continue

        raw_element_id = _attr(node, "id")
        stereotype_type = applied_stereotypes.get(raw_element_id, "")
        normalized_type = _normalize_type(xmi_type or tag, node, stereotype_type)
        if normalized_type == "Dependency":
            source = _first_ref(_attr(node, "client") or _attr(node, "source"))
            target = _first_ref(_attr(node, "supplier") or _attr(node, "target"))
            relation_type = _attr(node, "sysmlRelation") or node.attrib.get("name") or "dependency"
            if source and target:
                pending_relations.append((source, relation_type, target))
                report.converted.append(
                    {
                        "source": raw_element_id or node.attrib.get("name", ""),
                        "from": xmi_type or tag,
                        "to": relation_type,
                        "reason": "dependency mapped to repository relation",
                    }
                )
            else:
                report.skipped.append(
                    {
                        "source": raw_element_id or node.attrib.get("name", ""),
                        "type": xmi_type or tag,
                        "reason": "dependency is missing source or target",
                    }
                )
            continue
        if normalized_type == "Connector":
            endpoints = _connector_endpoints(node)
            if len(endpoints) >= 2:
                pending_relations.append((endpoints[0], "connect", endpoints[1]))
                report.converted.append(
                    {
                        "source": raw_element_id or node.attrib.get("name", ""),
                        "from": xmi_type or tag,
                        "to": "connect",
                        "reason": "connector endpoints mapped to connect relation",
                    }
                )
            else:
                report.skipped.append(
                    {
                        "source": raw_element_id or node.attrib.get("name", ""),
                        "type": xmi_type or tag,
                        "reason": "connector has fewer than two endpoints",
                    }
                )
            continue
        if normalized_type not in TYPE_PREFIX:
            report.skipped.append(
                {
                    "source": raw_element_id or node.attrib.get("name", ""),
                    "type": xmi_type or tag,
                    "reason": "unsupported UML/SysML type",
                }
            )
            continue

        element_id = raw_element_id or _next_id(normalized_type, generated_counts)
        attributes = _tagged_values(node)
        if xmi_type:
            attributes.setdefault("xmi_type", xmi_type)
        if xmi_type and xmi_type != TYPE_TO_UML.get(normalized_type, ""):
            report.converted.append(
                {
                    "source": element_id,
                    "from": xmi_type,
                    "to": normalized_type,
                    "reason": "UML type or applied stereotype mapped to repository element type",
                }
            )
        owner = _attr(node, "owner") or _attr(node, "ownerScope")
        parent = _nearest_parent_id(root, node)
        if parent:
            attributes.setdefault("parent", parent)
        element = {
            "id": element_id,
            "name": node.attrib.get("name") or element_id,
            "type": normalized_type,
            "stereotype": node.attrib.get("stereotype") or stereotype_type or default_stereotype(normalized_type),
            "description": _description(node),
            "owner": attributes.pop("owner", owner),
            "attributes": attributes,
            "relations": [],
        }
        elements[element_id] = element
        if parent and parent in elements:
            pending_relations.append((parent, "compose", element_id))

    for source, relation_type, target in pending_relations:
        if source in elements:
            if target in elements:
                elements[source].setdefault("relations", []).append({"type": relation_type, "target": target})
            else:
                elements[source].setdefault("relations", []).append({"type": relation_type, "target": target})
                report.downgraded.append(
                    {
                        "source": source,
                        "relation": relation_type,
                        "target": target,
                        "reason": "target is not represented as an imported repository element",
                    }
                )

    report.imported = len(elements)
    if report.downgraded:
        report.warnings.append("Some XMI relationships target elements that were not imported.")
    model = {
        "format": "xmi",
        "elements": list(elements.values()),
        "source": {"adapter": adapter, "tool": adapter},
        "mapping_report": report.to_dict(),
    }

    return AdapterParseResult(model, report)


def _qname(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _xml_declaration(payload: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{payload}'


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1] if "}" in name else name


def _attr(node: ET.Element, local_name: str) -> str:
    for key, value in node.attrib.items():
        if _local_name(key) == local_name:
            return value
    return ""


def _normalize_type(raw_type: str, node: ET.Element, stereotype_type: str = "") -> str:
    candidates = [
        stereotype_type,
        node.attrib.get("sysmlType", ""),
        node.attrib.get("stereotype", ""),
        raw_type.rsplit(":", 1)[-1],
        node.attrib.get("name", ""),
        _local_name(node.tag),
    ]
    for candidate in candidates:
        key = candidate.replace(" ", "").replace("-", "_").lower()
        if key in UML_TO_TYPE:
            return UML_TO_TYPE[key]
    if "depend" in raw_type.lower():
        return "Dependency"
    if "connector" in raw_type.lower():
        return "Connector"
    return ""


def _tagged_values(node: ET.Element) -> dict[str, str]:
    values: dict[str, str] = {}
    for child in node:
        if _local_name(child.tag) != "taggedValue":
            continue
        name = child.attrib.get("name")
        if name:
            values[name] = child.attrib.get("value", "")
    return values


def _description(node: ET.Element) -> str:
    for child in node:
        if _local_name(child.tag) == "ownedComment":
            return child.attrib.get("body") or "".join(child.itertext()).strip()
        if _local_name(child.tag) == "documentation":
            return child.attrib.get("value") or "".join(child.itertext()).strip()
    return ""


def _applied_stereotypes(root: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    base_keys = {
        "base_Class",
        "base_NamedElement",
        "base_Package",
        "base_Interface",
        "base_Property",
        "base_Activity",
        "base_State",
        "base_Constraint",
    }
    for node in root.iter():
        local = _local_name(node.tag)
        normalized = local.replace(" ", "").replace("-", "_").lower()
        if normalized not in UML_TO_TYPE:
            continue
        target = ""
        for key, value in node.attrib.items():
            if _local_name(key) in base_keys:
                target = _first_ref(value)
                break
        if target:
            result[target] = UML_TO_TYPE[normalized]
    return result


def _connector_endpoints(node: ET.Element) -> list[str]:
    endpoints = []
    for child in node:
        local = _local_name(child.tag)
        if local not in {"end", "ownedEnd"}:
            continue
        role = _first_ref(child.attrib.get("role", "") or child.attrib.get("partWithPort", ""))
        if role:
            endpoints.append(role)
    return endpoints


def _nearest_parent_id(root: ET.Element, target: ET.Element) -> str:
    for parent in root.iter():
        if target in list(parent):
            parent_id = _attr(parent, "id")
            return parent_id if parent_id and parent is not root else ""
    return ""


def _first_ref(value: str) -> str:
    return value.split()[0].lstrip("#") if value else ""


def _next_id(element_type: str, counts: dict[str, int]) -> str:
    counts[element_type] = counts.get(element_type, 0) + 1
    return f"{TYPE_PREFIX.get(element_type, 'ELM')}-{counts[element_type]:03d}"

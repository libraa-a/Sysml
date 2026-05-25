"""SysML-inspired metamodel, validation, and diagram helpers."""

from __future__ import annotations

import copy
from typing import Any


Element = dict[str, Any]


TYPE_PREFIX = {
    "Requirement": "REQ",
    "Block": "BLK",
    "Activity": "ACT",
    "Interface": "IF",
    "Port": "PRT",
    "Constraint": "CST",
    "State": "ST",
    "TestCase": "TST",
    "View": "VIEW",
    "Viewpoint": "VP",
}


TYPE_LABELS = {
    "Requirement": "需求",
    "Block": "结构块",
    "Activity": "活动",
    "Interface": "接口",
    "Port": "端口",
    "Constraint": "约束",
    "State": "状态",
    "TestCase": "测试用例",
    "View": "视图",
    "Viewpoint": "视角",
}


RELATION_LABELS = {
    "satisfy": "满足",
    "verify": "验证",
    "refine": "细化",
    "compose": "组成",
    "expose": "暴露端口",
    "connect": "连接",
    "allocate": "分配",
    "flow": "活动流",
    "transition": "状态迁移",
    "constrain": "约束",
    "include": "Include",
    "conform": "Conform",
}


METAMODEL = {
    "Requirement": {
        "stereotype": "requirement",
        "required_attributes": ["text", "verification"],
        "relations": {
            "satisfy": ["Block", "Activity", "Interface"],
            "verify": ["TestCase"],
            "refine": ["Requirement", "Activity"],
            "constrain": ["Constraint"],
        },
    },
    "Block": {
        "stereotype": "block",
        "required_attributes": [],
        "relations": {
            "satisfy": ["Requirement"],
            "compose": ["Block", "Port"],
            "expose": ["Port"],
            "connect": ["Interface", "Port", "Block"],
            "allocate": ["Activity"],
            "constrain": ["Constraint"],
        },
    },
    "Activity": {
        "stereotype": "activity",
        "required_attributes": ["trigger", "result"],
        "relations": {
            "satisfy": ["Requirement"],
            "flow": ["Activity"],
            "allocate": ["Block"],
            "refine": ["Requirement"],
        },
    },
    "Interface": {
        "stereotype": "interfaceBlock",
        "required_attributes": ["protocol"],
        "relations": {
            "satisfy": ["Requirement"],
            "connect": ["Block", "Port", "Interface"],
        },
    },
    "Port": {
        "stereotype": "proxyPort",
        "required_attributes": ["direction", "interface"],
        "relations": {
            "connect": ["Interface", "Port", "Block"],
        },
    },
    "Constraint": {
        "stereotype": "constraintBlock",
        "required_attributes": ["expression"],
        "relations": {
            "constrain": ["Requirement", "Block"],
        },
    },
    "State": {
        "stereotype": "state",
        "required_attributes": [],
        "relations": {
            "transition": ["State"],
        },
    },
    "TestCase": {
        "stereotype": "testCase",
        "required_attributes": ["method", "criterion"],
        "relations": {
            "verify": ["Requirement"],
        },
    },
    "View": {
        "stereotype": "view",
        "required_attributes": [],
        "relations": {
            "refine": ["Requirement", "Block", "Activity"],
            "include": list(TYPE_PREFIX),
            "conform": ["Viewpoint"],
        },
    },
    "Viewpoint": {
        "stereotype": "viewpoint",
        "required_attributes": [],
        "relations": {
            "refine": ["Requirement", "Block", "Activity", "View"],
        },
    },
}


DIAGRAM_TYPES = {
    "requirements": {
        "label": "需求追踪图",
        "types": ["Requirement", "Block", "Activity", "TestCase", "Constraint", "View", "Viewpoint"],
        "relations": ["satisfy", "verify", "refine", "constrain", "include", "conform"],
    },
    "structure": {
        "label": "块定义/接口图",
        "types": ["Block", "Port", "Interface", "Constraint"],
        "relations": ["compose", "expose", "connect", "constrain"],
    },
    "behavior": {
        "label": "活动/状态图",
        "types": ["Activity", "State", "Block"],
        "relations": ["flow", "transition", "allocate"],
    },
    "views": {
        "label": "View-Focused Graph",
        "types": list(TYPE_PREFIX),
        "relations": list(RELATION_LABELS),
    },
    "all": {
        "label": "全模型关系图",
        "types": list(TYPE_PREFIX),
        "relations": list(RELATION_LABELS),
    },
}


def metamodel_payload() -> dict[str, Any]:
    return {
        "types": copy.deepcopy(METAMODEL),
        "type_prefix": copy.deepcopy(TYPE_PREFIX),
        "type_labels": copy.deepcopy(TYPE_LABELS),
        "relation_labels": copy.deepcopy(RELATION_LABELS),
        "diagram_types": copy.deepcopy(DIAGRAM_TYPES),
    }


def default_stereotype(element_type: str) -> str:
    return METAMODEL.get(element_type, {}).get("stereotype", element_type.lower())


def validate_repository(elements: dict[str, Element]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for element in elements.values():
        issues.extend(validate_element(element, elements))
    from .views import validate_view_against_viewpoint

    for element in elements.values():
        if element.get("type") == "View":
            issues.extend(validate_view_against_viewpoint(elements, element))

    summary = {
        "errors": sum(1 for issue in issues if issue["severity"] == "error"),
        "warnings": sum(1 for issue in issues if issue["severity"] == "warning"),
        "infos": sum(1 for issue in issues if issue["severity"] == "info"),
        "elements": len(elements),
    }
    return {"summary": summary, "issues": issues}


def validate_element(element: Element, elements: dict[str, Element]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    element_id = str(element.get("id", ""))
    element_type = str(element.get("type", ""))
    attributes = element.get("attributes", {})

    if not element_id:
        issues.append(issue("error", element_id, "元素缺少 id"))
    if not element.get("name"):
        issues.append(issue("warning", element_id, "元素缺少名称"))
    if element_type not in METAMODEL:
        issues.append(issue("error", element_id, f"未知 SysML 类型 {element_type}"))
        return issues

    expected_stereotype = default_stereotype(element_type)
    if not element.get("stereotype"):
        issues.append(issue("info", element_id, f"未设置构造型，建议使用 {expected_stereotype}"))

    for required in METAMODEL[element_type]["required_attributes"]:
        if not attributes.get(required):
            issues.append(issue("warning", element_id, f"{element_type} 缺少属性 attributes.{required}"))

    allowed_relations = METAMODEL[element_type]["relations"]
    for relation in element.get("relations", []):
        relation_type = relation.get("type", "")
        target_id = relation.get("target", "")
        target = elements.get(target_id)
        if relation_type not in allowed_relations:
            issues.append(issue("warning", element_id, f"{element_type} 不建议使用关系 {relation_type}"))
            continue
        if not target:
            issues.append(issue("error", element_id, f"关系 {relation_type} 指向不存在的元素 {target_id}"))
            continue
        target_types = allowed_relations[relation_type]
        if target.get("type") not in target_types:
            expected = ", ".join(target_types)
            issues.append(
                issue(
                    "warning",
                    element_id,
                    f"关系 {relation_type} 的目标 {target_id} 类型为 {target.get('type')}，建议为 {expected}",
                )
            )

    if element_type == "Port":
        interface_id = attributes.get("interface")
        if interface_id and interface_id in elements and elements[interface_id].get("type") != "Interface":
            issues.append(issue("warning", element_id, f"端口 interface 指向 {interface_id}，但目标不是 Interface"))

    if element_type == "Viewpoint":
        for attribute_name in ("allowed_types", "required_types"):
            for type_name in attribute_list(attributes.get(attribute_name)):
                if type_name not in METAMODEL:
                    issues.append(issue("warning", element_id, f"Viewpoint {attribute_name} contains unknown type {type_name}"))
        for relation_name in attribute_list(attributes.get("allowed_relations")):
            if relation_name not in RELATION_LABELS:
                issues.append(issue("warning", element_id, f"Viewpoint allowed_relations contains unknown relation {relation_name}"))

    return issues


def issue(severity: str, element_id: str, message: str) -> dict[str, str]:
    return {"severity": severity, "element_id": element_id or "-", "message": message}


def attribute_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def build_diagram(elements: dict[str, Element], diagram_type: str = "requirements") -> dict[str, Any]:
    diagram = DIAGRAM_TYPES.get(diagram_type, DIAGRAM_TYPES["requirements"])
    included_types = set(diagram["types"])
    included_relations = set(diagram["relations"])
    selected = {
        element_id: element
        for element_id, element in elements.items()
        if element.get("type") in included_types
    }

    edges = []
    for source_id, element in selected.items():
        for relation in element.get("relations", []):
            target_id = relation.get("target")
            relation_type = relation.get("type")
            if target_id in selected and relation_type in included_relations:
                edges.append(
                    {
                        "source": source_id,
                        "target": target_id,
                        "type": relation_type,
                        "label": RELATION_LABELS.get(relation_type, relation_type),
                    }
                )

    nodes = layout_nodes(selected)
    return {
        "type": diagram_type,
        "label": diagram["label"],
        "nodes": nodes,
        "edges": edges,
    }


def layout_nodes(elements: dict[str, Element]) -> list[dict[str, Any]]:
    ordered_types = [
        "Requirement",
        "Block",
        "Port",
        "Interface",
        "Activity",
        "State",
        "Constraint",
        "TestCase",
        "View",
        "Viewpoint",
    ]
    grouped: dict[str, list[Element]] = {}
    for element in elements.values():
        grouped.setdefault(element.get("type", "Unknown"), []).append(element)

    nodes: list[dict[str, Any]] = []
    column = 0
    for element_type in ordered_types:
        items = sorted(grouped.get(element_type, []), key=lambda item: item.get("id", ""))
        if not items:
            continue
        for row, element in enumerate(items):
            nodes.append(
                {
                    "id": element.get("id", ""),
                    "name": element.get("name", ""),
                    "type": element_type,
                    "label": TYPE_LABELS.get(element_type, element_type),
                    "x": 90 + column * 230,
                    "y": 70 + row * 118,
                    "width": 170,
                    "height": 66,
                }
            )
        column += 1
    return nodes

"""DeepSeek-powered DocGen assistant service."""

from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any

import httpx
from fastapi import HTTPException

from ..docgen import build_traceability
from ..repository_contract import RepositoryStore


class AiDocgenService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store

    async def draft_docgen_template(
        self,
        project_id: str,
        branch: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        settings = self._settings()
        if not settings["api_key"]:
            raise HTTPException(
                status_code=503,
                detail="DeepSeek is not configured. Set DEEPSEEK_API_KEY before using the DocGen agent.",
            )

        project = self.store.get_project(project_id)
        branch_payload = self.store.get_branch(project_id, branch)
        elements = list(branch_payload.get("elements", {}).values())
        traceability = build_traceability(branch_payload.get("elements", {}))
        validation = self.store.validate_branch(project_id, branch)
        mode = payload.get("mode", "full")
        current_template = str(payload.get("template") or "")

        prompt = self._build_prompt(project, branch, elements, traceability, validation, mode, current_template)
        content = await self._chat(prompt, settings)
        draft = self._extract_markdown(content)

        return {
            "template": draft,
            "model": settings["model"],
            "mode": mode,
            "summary": self._model_summary(elements, validation),
        }

    async def review_model(self, project_id: str, branch: str, payload: dict[str, Any]) -> dict[str, Any]:
        settings = self._settings()
        if not settings["api_key"]:
            raise HTTPException(
                status_code=503,
                detail="DeepSeek is not configured. Set DEEPSEEK_API_KEY before using the VE review agent.",
            )

        project = self.store.get_project(project_id)
        branch_payload = self.store.get_branch(project_id, branch)
        elements = list(branch_payload.get("elements", {}).values())
        traceability = build_traceability(branch_payload.get("elements", {}))
        validation = self.store.validate_branch(project_id, branch)
        selected_id = str(payload.get("selected_id") or "")

        prompt = self._build_review_prompt(project, branch, elements, traceability, validation, selected_id)
        content = await self._chat(prompt, settings)
        review = self._extract_markdown(content)
        return {
            "review": review,
            "model": settings["model"],
            "summary": self._model_summary(elements, validation),
        }

    async def chat_about_model(self, project_id: str, branch: str, payload: dict[str, Any]) -> dict[str, Any]:
        settings = self._settings()
        if not settings["api_key"]:
            raise HTTPException(
                status_code=503,
                detail="DeepSeek is not configured. Set DEEPSEEK_API_KEY before using the model assistant.",
            )

        question = str(payload.get("question") or "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")

        project = self.store.get_project(project_id)
        branch_payload = self.store.get_branch(project_id, branch)
        elements = list(branch_payload.get("elements", {}).values())
        traceability = build_traceability(branch_payload.get("elements", {}))
        validation = self.store.validate_branch(project_id, branch)
        history = payload.get("history") if isinstance(payload.get("history"), list) else []

        prompt = self._build_chat_prompt(project, branch, elements, traceability, validation, question, history)
        answer = self._extract_markdown(await self._chat(prompt, settings))
        return {
            "answer": answer,
            "model": settings["model"],
            "summary": self._model_summary(elements, validation),
        }

    def _settings(self) -> dict[str, Any]:
        return {
            "api_key": os.environ.get("DEEPSEEK_API_KEY", "").strip(),
            "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat",
            "timeout": float(os.environ.get("DEEPSEEK_TIMEOUT", "45")),
        }

    async def _chat(self, prompt: str, settings: dict[str, Any]) -> str:
        url = f"{settings['base_url']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json",
        }
        body = {
            "model": settings["model"],
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a SysML DocGen assistant for a model-based systems engineering system. "
                        "Return only a Markdown DocGen template. Keep SysML data as placeholders where possible."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=settings["timeout"]) as client:
                response = await client.post(url, headers=headers, json=body)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:600]
            raise HTTPException(status_code=502, detail=f"DeepSeek API error: {detail}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Cannot reach DeepSeek API: {exc}") from exc

        data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="DeepSeek returned an unexpected response shape") from exc

    def _build_prompt(
        self,
        project: dict[str, Any],
        branch: str,
        elements: list[dict[str, Any]],
        traceability: dict[str, Any],
        validation: dict[str, Any],
        mode: str,
        current_template: str,
    ) -> str:
        compact_elements = [
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "name": item.get("name"),
                "description": item.get("description", ""),
                "relations": item.get("relations", [])[:8],
                "attributes": item.get("attributes", {}),
            }
            for item in elements[:80]
        ]
        context = {
            "project": {
                "id": project.get("id"),
                "name": project.get("name"),
                "description": project.get("description", ""),
                "organization": project.get("organization", ""),
                "branch": branch,
            },
            "model_summary": self._model_summary(elements, validation),
            "traceability": traceability[:40],
            "validation": validation,
            "sample_elements": compact_elements,
        }
        task = {
            "full": "Generate a complete engineering document template with chapters, summary, traceability explanation, and review comments.",
            "summary": "Generate a concise project summary and model overview section.",
            "trace": "Generate a traceability explanation section and keep the traceability matrix placeholder.",
            "review": "Generate model review comments and validation-oriented recommendations.",
        }.get(mode, "Generate a complete engineering document template.")
        return (
            f"{task}\n\n"
            "Use Chinese section titles and readable engineering prose.\n"
            "Keep these DocGen placeholders when relevant: {{model:summary}}, {{table:requirements}}, "
            "{{table:blocks}}, {{table:interfaces}}, {{table:constraints}}, {{table:tests}}, "
            "{{trace:matrix}}, {{validation:issues}}.\n"
            "Do not invent element IDs. If you mention model data, refer to the supplied context.\n"
            "Return only Markdown, no explanation outside the template.\n\n"
            f"Current template, if improving it:\n{current_template[:4000]}\n\n"
            f"Model context JSON:\n{json.dumps(context, ensure_ascii=False, indent=2)[:12000]}"
        )

    def _build_review_prompt(
        self,
        project: dict[str, Any],
        branch: str,
        elements: list[dict[str, Any]],
        traceability: list[dict[str, Any]],
        validation: dict[str, Any],
        selected_id: str,
    ) -> str:
        compact_elements = [
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "name": item.get("name"),
                "description": item.get("description", ""),
                "relations": item.get("relations", [])[:8],
                "attributes": item.get("attributes", {}),
            }
            for item in elements[:100]
        ]
        context = {
            "project": {
                "id": project.get("id"),
                "name": project.get("name"),
                "description": project.get("description", ""),
                "organization": project.get("organization", ""),
                "branch": branch,
            },
            "selected_id": selected_id,
            "model_summary": self._model_summary(elements, validation),
            "traceability": traceability[:60],
            "validation": validation,
            "elements": compact_elements,
        }
        return (
            "你是 VE 模型审查智能体，请对当前 SysML 模型做只读审查。"
            "重点检查需求是否清晰、需求是否有 satisfy/verify 闭环、模块和接口关系是否合理、"
            "约束和测试是否覆盖关键需求、校验问题是否需要优先处理。\n"
            "请输出中文 Markdown，结构固定为：\n"
            "## 总体评价\n## 可展示分析步骤\n## 关键问题\n## 追踪闭环建议\n## 元素级修改建议\n## 下一步行动\n"
            "可展示分析步骤只写面向用户的审查流程摘要，例如读取模型、统计元素、检查追踪关系、结合校验结果；不要输出隐藏推理链。\n"
            "不要编造不存在的元素 ID。不要输出 JSON。不要说你会直接修改模型，所有建议必须由工程师确认后执行。\n\n"
            f"模型上下文 JSON:\n{json.dumps(context, ensure_ascii=False, indent=2)[:14000]}"
        )

    def _build_chat_prompt(
        self,
        project: dict[str, Any],
        branch: str,
        elements: list[dict[str, Any]],
        traceability: list[dict[str, Any]],
        validation: dict[str, Any],
        question: str,
        history: list[Any],
    ) -> str:
        compact_elements = [
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "name": item.get("name"),
                "description": item.get("description", ""),
                "relations": item.get("relations", [])[:8],
                "attributes": item.get("attributes", {}),
            }
            for item in elements[:100]
        ]
        compact_history = [
            {
                "role": item.get("role"),
                "content": str(item.get("content") or "")[:1200],
            }
            for item in history[-6:]
            if isinstance(item, dict) and item.get("role") in {"user", "assistant"}
        ]
        context = {
            "project": {
                "id": project.get("id"),
                "name": project.get("name"),
                "description": project.get("description", ""),
                "organization": project.get("organization", ""),
                "branch": branch,
            },
            "model_summary": self._model_summary(elements, validation),
            "traceability": traceability[:60],
            "validation": validation,
            "elements": compact_elements,
            "chat_history": compact_history,
        }
        return (
            "你是 SysML 模型知识问答智能体。请只根据给定 MMS 模型上下文回答用户问题，"
            "可以解释需求、模块、接口、约束、测试、追踪关系、文档生成流程和模型质量。"
            "如果上下文中没有依据，请明确说明无法从当前模型确认。"
            "回答使用中文 Markdown，结构尽量包含：\n"
            "## 结论\n## 可展示分析步骤\n## 依据\n## 建议\n"
            "可展示分析步骤只写面向用户的处理流程摘要，例如读取模型上下文、匹配相关元素、检查追踪关系、汇总结论；不要输出隐藏推理链。\n"
            "优先给出结论，再列出依据元素 ID 或追踪关系。\n\n"
            f"用户问题：{question}\n\n"
            f"模型上下文 JSON:\n{json.dumps(context, ensure_ascii=False, indent=2)[:16000]}"
        )

    def _model_summary(self, elements: list[dict[str, Any]], validation: dict[str, Any]) -> dict[str, Any]:
        counts = Counter(str(item.get("type", "Unknown")) for item in elements)
        return {
            "element_count": len(elements),
            "type_counts": dict(counts),
            "validation": validation.get("summary", {}),
        }

    def _extract_markdown(self, content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

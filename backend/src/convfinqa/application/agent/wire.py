import json
from typing import Any, cast
from uuid import uuid4

from convfinqa.application.agent.tools import TOOL_REGISTRY
from convfinqa.domain.entities import Conversation
from convfinqa.domain.ports.llm import LLMToolSpec


def new_message_id() -> str:
    return f"msg_{uuid4().hex}"


def safe_json_loads(raw: str) -> dict[str, Any]:
    try:
        parsed: Any = json.loads(raw) if raw else {}
        if not isinstance(parsed, dict):
            return {}
        return cast(dict[str, Any], parsed)
    except (json.JSONDecodeError, ValueError):
        return {}


def build_tool_specs() -> list[LLMToolSpec]:
    return [
        LLMToolSpec(
            name=tool.name,
            description=tool.description,
            parameters=tool.input_schema.model_json_schema(),
        )
        for tool in TOOL_REGISTRY.values()
    ]


def history_to_wire(
    conversation: Conversation, user_text: str
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for m in conversation.messages:
        messages.append({"role": m.role.value, "content": m.content})
    messages.append({"role": "user", "content": user_text})
    return messages

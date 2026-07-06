import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient
from convfinqa.domain.entities import Document

ToolCalls = dict[str, dict[str, Any]]
MessageParts = list[dict[str, Any]]
WireMessages = list[dict[str, Any]]
SeenCitations = set[tuple[str, str]]


def doc_with_table() -> Document:
    return Document(
        id="doc1",
        ticker="JKHY",
        year=2009,
        page=None,
        title="Test",
        pre_text=None,
        post_text=None,
        table_data={"Year ended June 30, 2009": {"net cash from operations": "206588"}},
        column_order=None,
    )


def empty_doc() -> Document:
    return Document(
        id="doc1",
        ticker=None,
        year=None,
        page=None,
        title=None,
        pre_text=None,
        post_text=None,
        table_data=None,
        column_order=None,
    )


def make_tool_call(call_id: str, name: str, args: dict[str, object]) -> ToolCalls:
    raw = json.dumps(args)
    return {call_id: {"name": name, "args": raw, "args_chunks": [raw]}}


class RecordingObservability(NoOpLangfuseClient):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: list[dict[str, Any]] = []
        self.names: list[str] = []

    @asynccontextmanager
    async def start_as_current_observation(
        self,
        as_type: str,
        name: str,
        input: dict[str, Any] | None = None,
    ) -> AsyncGenerator[Any]:
        self.names.append(name)
        if input is not None:
            self.inputs.append(input)
        async with super().start_as_current_observation(
            as_type=as_type, name=name, input=input
        ) as span:
            yield span

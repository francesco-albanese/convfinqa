from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from convfinqa.application.use_cases.title_generation import generate_title
from convfinqa.domain.entities import Document
from convfinqa.domain.ports.llm import LLMChunk
from convfinqa.domain.ports.prompts import CompiledPrompt


@dataclass(slots=True)
class RecordingLLM:
    deltas: tuple[str, ...] = ("Cash ", "flow")
    seen_systems: list[str] = field(default_factory=list[str])
    seen_prompt_refs: list[Any] = field(default_factory=list[Any])

    async def stream(
        self,
        messages: Sequence[dict[str, Any]],
        system: str,
        tools: Any = None,
        generation_name: str | None = None,
        trace_user_id: str | None = None,
        session_id: str | None = None,
        environment: str | None = None,
        model: str | None = None,
        prompt_ref: Any = None,
    ) -> AsyncIterator[LLMChunk]:
        del tools, generation_name, trace_user_id, session_id, environment, model
        del messages
        self.seen_systems.append(system)
        self.seen_prompt_refs.append(prompt_ref)
        for delta in self.deltas:
            yield LLMChunk(text=delta)


@dataclass
class StaticPromptProvider:
    text: str
    version: int | None = None

    async def compile(
        self, name: str, label: str, variables: Mapping[str, object]
    ) -> CompiledPrompt:
        del name, label, variables
        return CompiledPrompt(text=self.text, version=self.version)


def _document() -> Document:
    return Document(
        id="doc-1",
        ticker="ACME",
        year=2024,
        page=1,
        title="ACME 2024 annual report",
        pre_text="pre",
        post_text="post",
        table_data={},
    )


async def test_generate_title_resolves_prompt_via_provider() -> None:
    llm = RecordingLLM()
    provider = StaticPromptProvider(text="Give a short title.")

    title = await generate_title(llm, provider, "what was revenue?", _document(), "m")

    assert title == "Cash flow"
    assert llm.seen_systems == ["Give a short title."]


async def test_generate_title_attaches_prompt_ref_when_version_is_resolved() -> None:
    llm = RecordingLLM()
    provider = StaticPromptProvider(text="Give a short title.", version=5)

    await generate_title(llm, provider, "what was revenue?", _document(), "m")

    prompt_ref = llm.seen_prompt_refs[0]
    assert prompt_ref.name == "convfinqa-title"
    assert prompt_ref.label == "production"
    assert prompt_ref.version == 5


async def test_generate_title_omits_prompt_ref_without_a_resolved_version() -> None:
    llm = RecordingLLM()
    provider = StaticPromptProvider(text="Give a short title.", version=None)

    await generate_title(llm, provider, "what was revenue?", _document(), "m")

    assert llm.seen_prompt_refs[0] is None


async def test_generate_title_uses_the_given_prompt_label() -> None:
    seen_labels: list[str] = []

    @dataclass
    class LabelCapturingProvider:
        async def compile(
            self, name: str, label: str, variables: Mapping[str, object]
        ) -> CompiledPrompt:
            del name, variables
            seen_labels.append(label)
            return CompiledPrompt(text="Give a short title.")

    llm = RecordingLLM()

    await generate_title(
        llm,
        LabelCapturingProvider(),
        "what was revenue?",
        _document(),
        "m",
        prompt_label="latest",
    )

    assert seen_labels == ["latest"]

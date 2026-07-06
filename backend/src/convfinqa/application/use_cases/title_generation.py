from convfinqa.domain.entities import Document
from convfinqa.domain.ports.llm import LLMPort, PromptRef
from convfinqa.domain.ports.prompts import PromptProviderPort

TITLE_MAX_CHARS = 80
TITLE_PROMPT_NAME = "convfinqa-title"


def build_title_seed(user_text: str, document: Document) -> str:
    descriptor = document.title or document.id
    ticker = document.ticker or "N/A"
    year = document.year if document.year is not None else "N/A"
    return (
        f"Document: {descriptor} (ticker {ticker}, year {year})\nQuestion: {user_text}"
    )


async def generate_title(
    llm: LLMPort,
    prompt_provider: PromptProviderPort,
    user_text: str,
    document: Document,
    model: str,
    prompt_label: str = "production",
) -> str | None:
    seed = build_title_seed(user_text, document)
    compiled_prompt = await prompt_provider.compile(TITLE_PROMPT_NAME, prompt_label, {})
    prompt_ref = (
        PromptRef(
            name=TITLE_PROMPT_NAME,
            label=prompt_label,
            version=compiled_prompt.version,
        )
        if compiled_prompt.version is not None
        else None
    )

    collected: list[str] = []
    async for chunk in llm.stream(
        [{"role": "user", "content": seed}],
        compiled_prompt.text,
        tools=None,
        generation_name="title-generation",
        model=model,
        prompt_ref=prompt_ref,
    ):
        collected.append(chunk.text)
    title = " ".join("".join(collected).split()).strip()
    if not title:
        return None
    return title[:TITLE_MAX_CHARS]

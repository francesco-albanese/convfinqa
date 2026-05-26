from convfinqa.domain.entities import Document
from convfinqa.domain.ports.llm import LLMPort

TITLE_SYSTEM_PROMPT = (
    "Generate a short 3-6 word title summarising the user's question about a "
    "financial document. Reply with the title only, no quotes, no punctuation "
    "at the end, no preamble."
)
TITLE_MAX_CHARS = 80


def build_title_seed(user_text: str, document: Document) -> str:
    descriptor = document.title or document.id
    ticker = document.ticker or "N/A"
    year = document.year if document.year is not None else "N/A"
    return (
        f"Document: {descriptor} (ticker {ticker}, year {year})\nQuestion: {user_text}"
    )


async def generate_title(
    llm: LLMPort,
    user_text: str,
    document: Document,
    model: str,
) -> str | None:
    seed = build_title_seed(user_text, document)
    collected: list[str] = []
    async for chunk in llm.stream(
        [{"role": "user", "content": seed}],
        TITLE_SYSTEM_PROMPT,
        tools=None,
        generation_name="title-generation",
        model=model,
    ):
        collected.append(chunk.text)
    title = " ".join("".join(collected).split()).strip()
    if not title:
        return None
    return title[:TITLE_MAX_CHARS]

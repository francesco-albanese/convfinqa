import json

from convfinqa.domain.entities import Document

MAX_TEXT_BYTES = 8 * 1024
TRUNCATION_MARKER = "\n…[truncated]…\n"


def _truncate_middle(text: str | None, max_bytes: int = MAX_TEXT_BYTES) -> str:
    if text is None:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    marker_bytes = TRUNCATION_MARKER.encode("utf-8")
    keep = max_bytes - len(marker_bytes)
    if keep <= 0:
        return TRUNCATION_MARKER
    half = keep // 2
    head = encoded[:half].decode("utf-8", errors="ignore")
    tail = encoded[-(keep - half) :].decode("utf-8", errors="ignore")
    return f"{head}{TRUNCATION_MARKER}{tail}"


def build_system_prompt(framing: str, document: Document) -> str:
    pre = _truncate_middle(document.pre_text)
    post = _truncate_middle(document.post_text)
    table_json = json.dumps(document.table_data or {}, separators=(",", ":"))
    title = document.title or document.id

    return (
        f"{framing}\n\n"
        f"You are answering questions about the following financial document.\n"
        f"Title: {title}\n"
        f"Ticker: {document.ticker or 'N/A'}\n"
        f"Year: {document.year if document.year is not None else 'N/A'}\n\n"
        f"--- Pre-table narrative ---\n{pre}\n\n"
        f"--- Table (JSON) ---\n{table_json}\n\n"
        f"--- Post-table narrative ---\n{post}\n"
    )

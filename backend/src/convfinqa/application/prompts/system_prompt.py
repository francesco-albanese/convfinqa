import json
from typing import Any

from convfinqa.domain.entities import Document


def _ordered_table(
    table_data: dict[str, Any] | None, column_order: tuple[str, ...] | None
) -> dict[str, Any]:
    if not table_data:
        return {}
    if column_order is None:
        return table_data
    ordered = {key: table_data[key] for key in column_order if key in table_data}
    for key, value in table_data.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def build_system_prompt(framing: str, document: Document) -> str:
    pre = document.pre_text or ""
    post = document.post_text or ""
    table = _ordered_table(document.table_data, document.column_order)
    table_json = json.dumps(table, separators=(",", ":"))
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

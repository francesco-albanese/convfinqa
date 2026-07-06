from html import escape
from typing import Any

from convfinqa.domain.entities import Document

TRUSTED_POLICY_START = "<trusted_application_policy>"
TRUSTED_POLICY_END = "</trusted_application_policy>"
UNTRUSTED_CONTEXT_START = "<untrusted_document_context>"
UNTRUSTED_CONTEXT_END = "</untrusted_document_context>"
UNTRUSTED_METADATA_START = "<untrusted_document_metadata>"
UNTRUSTED_METADATA_END = "</untrusted_document_metadata>"
UNTRUSTED_PRE_TEXT_START = "<untrusted_pre_table_narrative>"
UNTRUSTED_PRE_TEXT_END = "</untrusted_pre_table_narrative>"
UNTRUSTED_POST_TEXT_START = "<untrusted_post_table_narrative>"
UNTRUSTED_POST_TEXT_END = "</untrusted_post_table_narrative>"


def build_system_prompt_variables(document: Document, tool_docs: str) -> dict[str, Any]:
    return {
        "title": _escape_untrusted_text(document.title or document.id),
        "ticker": _escape_untrusted_text(document.ticker or "N/A"),
        "year": document.year if document.year is not None else "N/A",
        "page": document.page if document.page is not None else "N/A",
        "pre_text": _escape_untrusted_text(document.pre_text or ""),
        "post_text": _escape_untrusted_text(document.post_text or ""),
        "tool_docs": tool_docs,
    }


def _escape_untrusted_text(value: str) -> str:
    return escape(value, quote=True)

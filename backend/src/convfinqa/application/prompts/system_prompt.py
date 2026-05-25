from convfinqa.domain.entities import Document


def build_system_prompt(framing: str, document: Document) -> str:
    pre = document.pre_text or ""
    post = document.post_text or ""
    title = document.title or document.id

    return (
        f"{framing}\n\n"
        f"You are answering questions about the following financial document.\n"
        f"Title: {title}\n"
        f"Ticker: {document.ticker or 'N/A'}\n"
        f"Year: {document.year if document.year is not None else 'N/A'}\n\n"
        f"--- Pre-table narrative ---\n{pre}\n\n"
        f"--- Post-table narrative ---\n{post}\n"
    )

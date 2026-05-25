from convfinqa.application.agent.tools import TOOL_REGISTRY


def build_tool_docs() -> str:
    sections = [tool.doc_md for tool in TOOL_REGISTRY.values()]
    return "\n\n".join(sections)

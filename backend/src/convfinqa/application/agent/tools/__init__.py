import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from convfinqa.application.agent.sql.sql_query import (
    SQL_QUERY_DOC,
    SqlQueryInput,
    SqlQueryOutput,
    get_sql_query_callable,
)
from convfinqa.application.agent.tools.math import (
    ADD_DOC,
    DIVIDE_DOC,
    GREATER_THAN_DOC,
    MULTIPLY_DOC,
    SUBTRACT_DOC,
    MathInput,
    MathOutput,
    add,
    divide,
    greater_than,
    multiply,
    subtract,
)
from convfinqa.domain.entities import Document


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    callable: Callable[..., Any]  # noqa: A003
    doc_md: str
    timeout_s: float = 0.1


def _sql_query_sentinel(**_: Any) -> dict[str, Any]:
    raise NotImplementedError("sql_query requires document binding via get_sql_query_callable")


TOOL_REGISTRY: dict[str, Tool] = {
    "add": Tool(
        name="add",
        description="Add two string-encoded numbers and return the sum as a string.",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=add,
        doc_md=ADD_DOC,
        timeout_s=0.1,
    ),
    "subtract": Tool(
        name="subtract",
        description="Subtract b from a (both string-encoded numbers) and return the difference as a string.",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=subtract,
        doc_md=SUBTRACT_DOC,
        timeout_s=0.1,
    ),
    "multiply": Tool(
        name="multiply",
        description="Multiply two string-encoded numbers and return the product as a string.",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=multiply,
        doc_md=MULTIPLY_DOC,
        timeout_s=0.1,
    ),
    "divide": Tool(
        name="divide",
        description="Divide a by b (both string-encoded). Raises error if b is zero.",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=divide,
        doc_md=DIVIDE_DOC,
        timeout_s=0.1,
    ),
    "greater_than": Tool(
        name="greater_than",
        description='Compare two string-encoded numbers; returns "true" if a > b else "false".',
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=greater_than,
        doc_md=GREATER_THAN_DOC,
        timeout_s=0.1,
    ),
    "sql_query": Tool(
        name="sql_query",
        description=(
            "Execute a SELECT query against the pinned document's financial table cells. "
            "Always call sql_query before arithmetic to retrieve the exact cell values."
        ),
        input_schema=SqlQueryInput,
        output_schema=SqlQueryOutput,
        callable=_sql_query_sentinel,
        doc_md=SQL_QUERY_DOC,
        timeout_s=2.0,
    ),
}


def get_tool(name: str) -> Tool | None:
    return TOOL_REGISTRY.get(name)


def build_sql_query_tool(document: Document) -> Tool:
    return dataclasses.replace(
        TOOL_REGISTRY["sql_query"],
        callable=get_sql_query_callable(document),
    )

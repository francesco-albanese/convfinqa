import decimal
from typing import Any

from pydantic import BaseModel, Field

_NUMERIC_PATTERN = r"^-?\d+(\.\d+)?$"
_PRECISION = 28


def _ctx() -> decimal.Context:
    return decimal.Context(prec=_PRECISION)


class MathInput(BaseModel):
    a: str = Field(pattern=_NUMERIC_PATTERN)
    b: str = Field(pattern=_NUMERIC_PATTERN)


class MathOutput(BaseModel):
    result: str


def add(a: str, b: str) -> dict[str, Any]:
    ctx = _ctx()
    result = ctx.add(decimal.Decimal(a), decimal.Decimal(b))
    return {"result": str(result)}


def subtract(a: str, b: str) -> dict[str, Any]:
    ctx = _ctx()
    result = ctx.subtract(decimal.Decimal(a), decimal.Decimal(b))
    return {"result": str(result)}


def multiply(a: str, b: str) -> dict[str, Any]:
    ctx = _ctx()
    result = ctx.multiply(decimal.Decimal(a), decimal.Decimal(b))
    return {"result": str(result)}


def divide(a: str, b: str) -> dict[str, Any]:
    ctx = _ctx()
    divisor = decimal.Decimal(b)
    if divisor == decimal.Decimal(0):
        raise ValueError("division by zero")
    result = ctx.divide(decimal.Decimal(a), divisor)
    return {"result": str(result)}


def greater_than(a: str, b: str) -> dict[str, Any]:
    ctx = _ctx()
    da = ctx.create_decimal(a)
    db = ctx.create_decimal(b)
    return {"result": "true" if da > db else "false"}


ADD_DOC = """\
## add(a, b)
Purpose: Add two numbers.
Args: a (string-encoded number), b (string-encoded number).
Returns: string-encoded sum.
When to use: When you need to sum two values from the document.
Example: add(a="206588", b="181001") → "387589"\
"""

SUBTRACT_DOC = """\
## subtract(a, b)
Purpose: Subtract b from a.
Args: a (string-encoded number), b (string-encoded number).
Returns: string-encoded difference.
When to use: When you need to find the change or delta between two values.
Example: subtract(a="206588", b="181001") → "25587"\
"""

MULTIPLY_DOC = """\
## multiply(a, b)
Purpose: Multiply two numbers.
Args: a (string-encoded number), b (string-encoded number).
Returns: string-encoded product.
When to use: When you need to scale a value by a factor (e.g., per-share values, percentage rates).
Example: multiply(a="3.14", b="100") → "314.00"\
"""

DIVIDE_DOC = """\
## divide(a, b)
Purpose: Divide a by b.
Args: a (string-encoded numerator), b (string-encoded non-zero denominator).
Returns: string-encoded quotient.
When to use: When computing ratios, averages, or per-unit values.
Raises: error if b is zero.
Example: divide(a="387589", b="2") → "193794.5"\
"""

GREATER_THAN_DOC = """\
## greater_than(a, b)
Purpose: Compare two numbers and check whether a is strictly greater than b.
Args: a (string-encoded number), b (string-encoded number).
Returns: "true" if a > b, otherwise "false".
When to use: When you need to determine which of two values is larger.
Example: greater_than(a="206588", b="181001") → "true"\
"""

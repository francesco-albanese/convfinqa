# Math tool catalog: exactly 5 tools, Decimal end-to-end, derived from dataset

Date: 25-05-2026

## Context

The agent loop needs deterministic arithmetic primitives to make every numeric answer verifiable and unit-testable. We must choose: a generic `arithmetic(expression)` tool, a small family of named operators, or a fuller numerical library.

An empirical pass over `dialogue.turn_program` across both ConvFinQA splits (12,594 program steps) shows the operator distribution: subtract 5,131 (40.7%) · divide 4,280 (34.0%) · add 2,457 (19.5%) · multiply 894 (7.1%) · greater 40 (0.3%) · exp 4 (0.0%). Five operators cover 99.97% of the corpus. Conv_answers are lossy-rounded formats of executed_answer floats (`0.14136` → `"14.1%"`), so internal arithmetic must avoid float drift on chained operations.

## Decision

Exactly five Math Tools: `add(a, b)`, `subtract(a, b)`, `multiply(a, b)`, `divide(a, b)`, `greater_than(a, b)`. Skip `exp` (4 dataset cases — negligible). Each tool declares its `a` and `b` args as JSON `string` (numeric pattern), parses to `decimal.Decimal` with default 28-digit context, computes exactly, and returns a stringified Decimal. `divide` rejects divisor `0` with an explicit `is_error=true` ToolResult. No `arithmetic(expression)` tool — per-operation granularity is the point (each step is auditable in the trace and unit-testable in isolation).

## Considered and rejected

- **Float + boundary rounding** — masks drift rather than preventing it; chained `subtract → divide` still drifts before rounding.
- **`fractions.Fraction`** — mathematically exact but JSON-serialisation story is awkward and conversion to `"14.1%"` display is fiddly.
- **Generic `arithmetic(expr)` tool** — collapses the reasoning trace to one step instead of three; loses per-operation testability that was an explicit requirement.
- **6th tool `power(base, exponent)`** — 4 dataset cases is below the threshold; the LLM can chain `multiply` if it really needs squares.

## Consequences

LLM tool schemas declare numeric args as `string`; system prompt must teach the model to quote numbers. The Eval Grader, not the math tools, owns the formatting of the prose answer (Decimal full precision in; lossy rounded percent/decimal/integer out at the answer-extraction layer).

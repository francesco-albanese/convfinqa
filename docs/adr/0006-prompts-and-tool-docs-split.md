# System prompt and tool docs are separate modules; tools are invocable from their pydantic schemas alone

Date: 25-05-2026

## Context

Today `application/prompts/system_prompt.py` is one function that builds the entire LLM-facing prompt. The agent-architecture epic adds tool use (5 Math Tools + `sql_query` Lookup Tool), each with non-trivial documentation: the Cells schema, the "quote numeric args" rule for Decimal handling, the "prefer `sql_query` before arithmetic" instruction, plus per-tool argument-shape examples. Collapsing all of that into one function makes it impossible to ablation-test "does the LLM still call the tools correctly when we *remove* the tool docs from the system prompt?" — a question we explicitly want to answer in beads epic `convfinqa-gyv`.

## Decision

Two modules:

1. **`application/prompts/system_prompt.py`** — narrative framing, role, behavioural directives, the pinned Document's pre-text/post-text/title/ticker. Does NOT mention tool names, tool args, or the Cells schema.
2. **`application/prompts/tool_docs.py`** — per-tool natural-language documentation strings (purpose, args, return shape, when-to-use, examples). One docstring per tool, addressable by tool name.

The Agent Loop assembles the final LLM request by concatenating: `system_prompt + tool_docs`. The ablation switch is a single boolean — include `tool_docs` or omit it — and the Tool registry passes the same pydantic input/output schemas to the LLM tool-use API surface in both arms. **Tools must remain invocable from their schemas alone** — i.e. when `tool_docs` is omitted, the model still sees `sql_query: {input_schema: {sql: string}}` etc. via the provider's tool-use mechanism. The pydantic schema is the load-bearing contract; the natural-language docs are coaching, not specification.

## Considered and rejected

- **Keep everything in `system_prompt.py`** — cannot ablation-test prompt-versus-schema; modifying the prompt risks accidentally removing tool docs and silently degrading tool selection without a way to detect it.
- **One module per tool, prompt-shipped inline alongside the tool** — collocates tool implementation with its docs but couples the prompt-assembly path to the registry's import order; harder to reason about prompt size budgets.

## Consequences

A Tool's registration becomes a tuple `(name, callable, input_schema, output_schema, doc_md)` where `doc_md` is optional and consumed by `tool_docs.py`. The `convfinqa-gyv` epic gains a concrete ablation: same dev-set, same model, same Math+Lookup tools, two arms — `WITH_TOOL_DOCS` vs `WITHOUT_TOOL_DOCS` — to measure whether the LLM relies on the natural-language coaching or whether the pydantic schema + tool-use surface is sufficient. If the second arm performs comparably, we can shrink the prompt and save tokens.

# Two-column trace persistence: `messages.parts` JSONB + `messages.reasoning_signatures` JSONB

Date: 25-05-2026

## Context

The Agent Loop produces a rich per-turn trace (reasoning blocks, tool calls, tool results, citations, final text). The history view (GET chat messages) must replay this trace without re-running the LLM. Additionally, Anthropic Extended Thinking requires that the encrypted `signature` of each reasoning block be passed back unmodified to the model on follow-up turns of the same Conversation to maintain reasoning continuity during tool-use loops; the signature must NEVER be served to clients.

## Decision

Two JSONB columns on `messages`:

1. **`parts JSONB NULL`** — schema-versioned (`{schema_version: 1, parts: [...]}`) ordered list of UIMessage-format parts as a discriminated union keyed by `kind` (`reasoning | tool_call | tool_result | citation | text`). Written by the Agent Loop on turn completion; read by the GET-chat-messages endpoint; validated on write by a pydantic model; size-capped (reasoning ≤16 KB, tool args ≤4 KB, tool result ≤32 KB, text ≤64 KB, array ≤256 items, total ≤256 KB) with truncate-with-marker on overflow. **Served to clients.**
2. **`reasoning_signatures JSONB NULL`** — Anthropic-only. Map of `{reasoning_block_id → signature}`. Read only by the Agent Loop when constructing the next-turn message list. **NEVER served by the API.** NULL for Gemini conversations (Gemini's "thought summaries" carry no equivalent).

Tool results round-trip back to the LLM under the provider's tool-result role (Anthropic `tool_result`, OpenAI/Gemini `tool`), never `user` — the canonical prompt-injection-elevation defence in agent loops.

## Considered and rejected

- **Single `parts` JSONB with the API serialiser stripping `signature`** — fragile defence (one buggy commit leaks signatures); two columns enforce the boundary at the schema layer.
- **Sibling `message_parts` table** — normalised, but ~10 rows per turn, joins on read, and heavier migration for no real query benefit.
- **No trace persistence** — replay-view shows only final text, history loses the mockup-E numbered-step trace, eval harness has to rerun the LLM. Rejected.

## Consequences

Two alembic migrations: add `parts` column, add `reasoning_signatures` column. New pydantic schema for parts validation. The GET-chat-messages endpoint's response model gains a `parts` field that replays the full trace. Multi-turn replay on Anthropic reads both columns; on Gemini reads only `parts`.

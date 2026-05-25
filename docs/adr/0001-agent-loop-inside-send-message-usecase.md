# Agent loop lives inside SendMessageUseCase, not a separate use case

Date: 25-05-2026

## Context

Mockup E and `TODO.md:2 + 11 + 14 + 15` require the assistant to interleave reasoning, deterministic tool calls (math + sql_query), and a final text answer, all streamed live. Today `SendMessageUseCase.stream(...)` is a single-shot LLM-text-streaming use case with six event types and no tool concept.

## Decision

The Agent Loop replaces the body of `SendMessageUseCase.stream(...)`. Same public surface — `AsyncGenerator[StreamEvent]`, same dependency injection. The event vocabulary expands to add: `ReasoningStart/Delta/End`, `ToolCallStart`, `ToolCallArgsDelta`, `ToolCallArgsComplete`, `ToolResult`, `Citation`, plus a new `Finish(stop_reason=ITERATION_CAP)` variant. Hard cap of 10 LLM↔tool iterations per user turn; per-tool timeout (sql_query 2 s, math 100 ms); on tool error emit `ToolResult(is_error=true)` back to the LLM for self-correction rather than aborting the turn.

## Considered and rejected

A parallel `AgentLoopUseCase` behind a feature flag (twice the surface to maintain, two persistence shapes) and a background-worker agent runtime (heavy refactor for what is still synchronous SSE today).

## Consequences

`entrypoints/api/sse.py` gains case branches for the new event types. The `/v1/chat` sync presenter (which assembles a snapshot) and `/v1/chat/stream` (SSE) both consume the same generator — the hexagonal rule "one generator, two presenters" still holds, just with more parts to assemble.

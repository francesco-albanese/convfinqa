# Sandboxed code execution deferred behind `CODE_EXEC_BACKEND=disabled` flag stub

Date: 25-05-2026

## Context

`TODO.md:14` calls for an optional sandboxed code-execution tool — both as a *production* fallback for arithmetic the deterministic math tools can't express and as a *research arm* for the ablation "do LLMs do basic maths well *without* tools?". The empirical evidence (ADR-0003) shows 99.97% of ConvFinQA arithmetic is covered by five deterministic operators, so production necessity is weak. AWS-native managed sandboxing exists (Amazon Bedrock AgentCore Code Interpreter — Firecracker microVM, per-session billing, GA late 2025), and a DIY locked-down-Lambda alternative is feasible.

## Decision

Out of scope for the agent-architecture epic. Ship the epic with `CODE_EXEC_BACKEND=disabled` (env var) and no `python_exec` tool registered. The follow-up epic, tracked in beads, will:

1. Define a `CodeExecPort` Protocol in `domain/ports/`.
2. Provide two adapters: `agentcore.py` (Bedrock AgentCore Code Interpreter — managed Firecracker microVM, one session per turn) and `lambda.py` (locked execution role, 512 MB / 30 s, no VPC egress, ephemeral storage cleared).
3. Switch via `CODE_EXEC_BACKEND=disabled | agentcore | lambda` at composition root (`container.py`).
4. Register the `python_exec(code: str) → stdout` tool only when backend is not `disabled`.
5. Provide an ablation harness (eval run with code-exec on vs off) to validate the research question.

## Considered and rejected

- **Build AgentCore now** — significantly expands this epic's scope and AWS bill (per-session-minute), without empirical evidence the deterministic-tool path leaves accuracy on the table.
- **Build locked-Lambda now** — same scope expansion plus DIY security ownership; no benefit until the deterministic-tool baseline ships and the ablation can actually be measured.

## Consequences

The agent-loop architecture (ADR-0001) already accommodates additional tools without restructure — adding `python_exec` later is a registry insertion plus a new event-stream pass-through (the same `ToolCallStart / ToolResult` events work for any tool). The deferral is reversible at low cost.

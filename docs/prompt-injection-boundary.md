# Prompt Injection Boundary

Date: 2026-06-02

## Implemented Boundary

`application/prompts/system_prompt.py` now renders the LLM system prompt as two explicit sections:

- `<trusted_application_policy>` contains immutable application framing and boundary rules.
- `<untrusted_document_context>` contains pinned Document metadata and narrative fields.

Document title, ticker, year, page, pre-table narrative, post-table narrative, table row labels, table column labels, and table values are treated as untrusted data. Table row labels, column labels, and values are not inlined into the system prompt; they remain available through the existing Lookup tool contract. Tool docs are still appended separately by `SendMessageUseCase`, preserving the system-prompt/tool-doc split in ADR 0006.

Direct user text remains in normal user-role wire messages and is not copied into trusted policy.

## Regression Harness

The initial harness is local and deterministic. It covers:

- direct user prompt injection staying out of the system prompt;
- malicious Document metadata staying outside trusted policy;
- malicious pre-table and post-table narrative staying outside trusted policy;
- malicious table row labels, column labels, and values not being inlined into the prompt.

The tests assert boundary contracts and externally relevant behavior rather than exact prompt formatting.

## Residual Risks

This slice does not detect or block prompt injection. It only makes the policy/data boundary explicit and testable.

The model can still ignore boundary instructions. Later slices must add deterministic detection, domain refusal, tool gating, output guarding, and operational signals.

The Lookup tool still exposes table contents to the model during tool use. Future ToolPolicyGate work must validate model-emitted tool calls before execution and treat all returned table text as untrusted observations.

Streaming output is not guarded yet. Unsafe partial output can still cross the SSE boundary until OutputGuard lands.

## Follow-Up Slices

- `convfinqa-vmf.2`: domain-boundary refusals.
- `convfinqa-vmf.3`: deterministic prompt-injection detector.
- `convfinqa-vmf.4`: tool policy gate.
- `convfinqa-vmf.5`: output guard for leakage and rendering.
- `convfinqa-vmf.6`: security signals and suspicious-attempt hooks.
- `convfinqa-vmf.7`: opt-in live provider regression campaign.

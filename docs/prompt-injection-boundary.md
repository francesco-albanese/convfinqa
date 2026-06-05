# Prompt Injection Boundary

Date: 2026-06-02

## Implemented Boundary

`application/prompts/system_prompt.py` now renders the LLM system prompt as two explicit sections:

- `<trusted_application_policy>` contains immutable application framing and boundary rules.
- `<untrusted_document_context>` contains pinned Document metadata and narrative fields.

Document title, ticker, year, page, pre-table narrative, post-table narrative, table row labels, table column labels, and table values are treated as untrusted data. Table row labels, column labels, and values are not inlined into the system prompt; they remain available through the existing Lookup tool contract. Tool docs are still appended separately by `SendMessageUseCase`, preserving the system-prompt/tool-doc split in ADR 0006.

Direct user text remains in normal user-role wire messages and is not copied into trusted policy.

`application/domain_boundary.py` now adds a deterministic user-turn boundary before generation. The `SendMessageUseCase` persists the user's message, starts the assistant response, and then either:

- allows pinned-Document financial questions through the existing Agent loop; or
- writes a constrained assistant response without calling the LLM.

The first blocked classes are off-domain general knowledge, unrelated code requests, current or live stock-price requests, role-change attempts, protected-internal questions, and cross-document requests. Safe app-capability questions are answered directly with a minimal description of document-grounded capabilities and an explicit refusal to reveal hidden instructions, internal policies, or exact tool schemas.

## Regression Harness

The initial harness is local and deterministic. It covers:

- direct user prompt injection staying out of the system prompt;
- direct user prompt injection being refused before an LLM call;
- off-domain, unrelated code, current stock-price, role-change, and cross-document turns being refused by the domain policy;
- pinned-Document financial questions proceeding through the existing Agent loop;
- safe app-capability questions receiving a constrained local response;
- malicious Document metadata staying outside trusted policy;
- malicious pre-table and post-table narrative staying outside trusted policy;
- malicious table row labels, column labels, and values not being inlined into the prompt.

The tests assert boundary contracts and externally relevant behavior rather than exact prompt formatting.

## Residual Risks

This slice blocks obvious domain-boundary violations, but it is not a full prompt-injection detector. The matching is deterministic and intentionally narrow; obfuscated attacks, multilingual attacks, encoded payloads, and indirect injection remain for the detector slice.

The model can still ignore boundary instructions for turns that pass the domain policy. Later slices must add deterministic injection detection, tool gating, output guarding, and operational signals.

The Lookup tool still exposes table contents to the model during tool use. Future ToolPolicyGate work must validate model-emitted tool calls before execution and treat all returned table text as untrusted observations.

Streaming output is not guarded yet. Unsafe partial output can still cross the SSE boundary until OutputGuard lands.

Domain-boundary matching uses document-grounding heuristics and cannot prove semantic relevance. It may refuse terse legitimate follow-ups that lack document or financial terms, and it may allow some broad financial prompts for the model to handle under the trusted policy. Follow-up context-aware classification should use prior turns and the pinned Document more precisely.

## Follow-Up Slices

- `convfinqa-vmf.3`: deterministic prompt-injection detector.
- `convfinqa-vmf.4`: tool policy gate.
- `convfinqa-vmf.5`: output guard for leakage and rendering.
- `convfinqa-vmf.6`: security signals and suspicious-attempt hooks.
- `convfinqa-vmf.7`: opt-in live provider regression campaign.

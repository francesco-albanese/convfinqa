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

`application/prompt_injection_detector.py` now adds a deterministic detector for obvious prompt-injection attempts before user turns reach model generation. It returns typed decisions and findings (`allow`, `observe`, `warn`, `block`) with stable attack-family, surface, and matched-on metadata so later slices can reuse the same boundary for tool gating, output guarding, and security signals.

The initial blocking families are direct instruction override, system/developer prompt extraction, fake role delimiters, encoded payloads, typoglycemia-style override variants, multilingual override phrases, refusal suppression, and safety-label manipulation. Zero-width controls are reported separately; zero-width-only text warns, while zero-width text that normalizes into a blocking family is blocked.

The detector can scan raw user text, prior turns, Document metadata, Document narrative, Table labels, Table values, and forged tool-result-shaped text. In this slice, `SendMessageUseCase` enforces blocking decisions only for the current user turn before persistence and before any LLM call. Document, prior-turn, Table, and tool-result surfaces are covered by regression tests and exposed through the typed API for later slices.

`application/agent/tool_policy_gate.py` now checks model-emitted tool calls at the replay boundary before execution. The gate allows known Math tools only with their exact argument schemas, and allows `sql_query` only when its JSON args contain a single SQL string scoped to the pinned Document's per-call `cells` table. SQL policy rejects catalog/schema probing, `SELECT *`, unscoped broad table reads, comments, semicolon chains, DDL/DML, unknown tables or columns, cross-user/cross-document identifiers, malformed args, unknown tools, and forged tool-result-shaped arguments. Blocked tool calls fail closed with a generic `{"error": "tool call blocked"}` result that is safe for the user SSE stream and for the provider's next iteration.

## Regression Harness

The initial harness is local and deterministic. It covers:

- direct user prompt injection staying out of the system prompt;
- direct user prompt injection being refused before an LLM call;
- encoded, zero-width, typoglycemia, multilingual, fake-role, refusal-suppression, and safety-label prompt-injection decisions;
- prior-turn, Document metadata, Document narrative, Table-label, Table-value, and forged-tool-result detector surfaces;
- valid `sql_query` and Math calls continuing to execute through replay;
- blocked SQL, malformed args, unknown tools, and forged tool-result-shaped arguments returning sanitized tool errors;
- off-domain, unrelated code, current stock-price, role-change, and cross-document turns being refused by the domain policy;
- pinned-Document financial questions proceeding through the existing Agent loop;
- safe app-capability questions receiving a constrained local response;
- malicious Document metadata staying outside trusted policy;
- malicious pre-table and post-table narrative staying outside trusted policy;
- malicious table row labels, column labels, and values not being inlined into the prompt.

The tests assert boundary contracts and externally relevant behavior rather than exact prompt formatting.

## Residual Risks

This slice blocks obvious domain-boundary violations and high-confidence user-turn prompt injection. The detector matching is deterministic and intentionally narrow.

The model can still ignore boundary instructions for turns that pass the domain policy and detector. Later slices must add tool gating, output guarding, and operational signals.

The Lookup tool still exposes table contents to the model during allowed tool use. The ToolPolicyGate restricts queries to the per-call `cells` table, but it does not prove semantic relevance beyond row/column scoping and identifier checks. Returned table text remains an untrusted observation for later output guarding.

Streaming output is not guarded yet. Unsafe partial output can still cross the SSE boundary until OutputGuard lands.

Domain-boundary matching uses document-grounding heuristics and cannot prove semantic relevance. It may refuse terse legitimate follow-ups that lack document or financial terms, and it may allow some broad financial prompts for the model to handle under the trusted policy. Follow-up context-aware classification should use prior turns and the pinned Document more precisely.

Detector matching will miss paraphrases, mixed-language payloads outside the small phrase list, encoded formats other than the local base64/hex decoding paths, and semantic attacks that do not use recognizable control-plane language. It may also warn on legitimate text containing zero-width controls. The detector does not emit security signals yet; that belongs to `convfinqa-vmf.6`.

## Follow-Up Slices

- `convfinqa-vmf.5`: output guard for leakage and rendering.
- `convfinqa-vmf.6`: security signals and suspicious-attempt hooks.
- `convfinqa-vmf.7`: opt-in live provider regression campaign.

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

`application/output_guard.py` now checks assistant text before it crosses the user boundary or persistence boundary. Streaming text is held behind a small suffix buffer, inspected incrementally, and emitted only after the guard clears it. High-risk output is replaced with a fixed safe refusal. If a later chunk is blocked after an earlier safe prefix was already streamed, persisted `messages.content` and text parts are still replaced with only the refusal.

The first output block classes are prompt leakage, exact tool-schema leakage, reasoning-signature leakage, AWS/JWT/cookie/DSN/internal-path-shaped strings, unsupported cross-document claims, citation-forgery markup, and unsafe HTML or Markdown link/image payloads.

`application/security_signals.py` now emits structured security events for every guardrail decision, on the dedicated `convfinqa.security` logger with stable event names:

- `domain_boundary_blocked` — domain policy refusals (all reasons except the benign `app_capability` answer), with `conversation_id`, `document_id`, `model`, and `reason`.
- `prompt_injection_detected` — any non-allow detector decision, with `action`, sorted deduplicated attack `families` and `surfaces`, and `detector_failed=true` when the detector itself crashed and the turn failed closed.
- `tool_policy_blocked` — ToolPolicyGate blocks at the replay boundary, with `tool_name` and the gate `reason`.
- `output_guard_blocked` — StreamingOutputGuard blocks, with the guard `reason`.
- `provider_throttled` — upstream LLM failures classified as `rate_limited`, `budget_exceeded`, or `context_window_exceeded` from the exception shape (HTTP 429 status or throttle/budget/context-window class names), without importing provider SDKs into the application layer.
- `cost_control_triggered` — the agent loop hitting its iteration cap.
- `suspicious_activity_throttled` — see below.
- `security_regression_failed` — reserved for the opt-in live regression campaign (`convfinqa-vmf.7`).

Signal metadata is limited to identifiers, enum values, and counts. Raw user text, document content, hidden prompts, tool schemas, reasoning signatures, cookies, JWTs, and Authorization material are never logged; the regression tests assert the attack payload does not appear in any emitted field.

`application/suspicious_attempt_throttle.py` adds the first suspicious-attempt throttling hook. User-attributable guardrail blocks (prompt-injection blocks and the adversarial domain reasons `protected_internals` and `role_change`) increment a per-user counter through the existing `RateLimitPort` (Postgres `rate_limit` table, epoch-floored windows, default 5 blocked attempts per 300s configured by `SUSPICIOUS_ATTEMPT_MAX_BLOCKS` / `SUSPICIOUS_ATTEMPT_WINDOW_SECONDS`). Once the count exceeds the limit, further blocked turns receive a generic slow-down refusal instead of the detailed policy refusal, which also reduces guardrail-oracle probing value. Output-guard blocks emit signals but do not count toward throttling because they can be caused by poisoned document content rather than the user. Throttle bookkeeping fails open: if the rate-limit backend errors, the turn still gets the normal guardrail refusal.

## Regression Harness

The initial harness is local and deterministic. It covers:

- direct user prompt injection staying out of the system prompt;
- direct user prompt injection being refused before an LLM call;
- encoded, zero-width, typoglycemia, multilingual, fake-role, refusal-suppression, and safety-label prompt-injection decisions;
- prior-turn, Document metadata, Document narrative, Table-label, Table-value, and forged-tool-result detector surfaces;
- valid `sql_query` and Math calls continuing to execute through replay;
- blocked SQL, malformed args, unknown tools, and forged tool-result-shaped arguments returning sanitized tool errors;
- output guard decisions for prompt leakage, tool schema leakage, reasoning signatures, secret-shaped content, cross-document claims, citation forgery, and unsafe markup;
- streaming split-pattern leakage being replaced before unsafe `text-delta` frames are emitted;
- guarded output persisting only the safe refusal in assistant content and text parts;
- security signals emitting stable event names with safe metadata for injection blocks, domain blocks, tool-policy blocks, output-guard blocks, and provider throttling;
- suspicious-attempt throttling switching repeated blocked turns to the generic slow-down refusal without any live provider call;
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

The OutputGuard is deterministic and intentionally narrow. It blocks obvious leakage and markup hazards, but it does not prove every answer is fully supported by citations or by the pinned Document. It also uses bounded suffix buffering for streaming, so long benign prefixes may be emitted before a later unsafe pattern is blocked; persisted content is replaced with the refusal when a block occurs.

Domain-boundary matching uses document-grounding heuristics and cannot prove semantic relevance. It may refuse terse legitimate follow-ups that lack document or financial terms, and it may allow some broad financial prompts for the model to handle under the trusted policy. Follow-up context-aware classification should use prior turns and the pinned Document more precisely.

Detector matching will miss paraphrases, mixed-language payloads outside the small phrase list, encoded formats other than the local base64/hex decoding paths, and semantic attacks that do not use recognizable control-plane language. It may also warn on legitimate text containing zero-width controls.

Suspicious-attempt throttling only inspects turns that a guardrail already blocked; allowed prompts are never throttled by this slice, so a patient attacker staying under the block threshold is not slowed down. The counter is per user, so unauthenticated deployments (Cognito disabled) throttle on whatever identity the trust boundary provides. Throttling state lives in the shared `rate_limit` table keyed only by `(user_id, window_start)`; if a future general request rate limit reuses the same table with the same window arithmetic, the two counters will collide — split the key or the table before shipping that. A full abuse platform (cross-session reputation, IP heuristics, automated lockout) remains out of scope.

## Live Provider Regression Campaign (`convfinqa-vmf.7`)

`application/security_regression_cases.py` defines a small, representative attack corpus (`REPRESENTATIVE_CASES`) covering all seven categories called out in the PRD: direct user prompt injection, indirect injection planted in Document narrative, indirect injection planted in Document metadata (title/ticker), indirect injection planted in an unrelated Table row label, a forged/unscoped tool-call attempt, direct requests for secret- or reasoning-shaped output leakage, and a multi-turn poisoning attempt (a blocked turn one must not hijack turn three). Each case pins a throwaway fixture Document and asserts a mix of: the turn must be blocked before the model is called (verified via captured `domain_boundary_blocked` / `prompt_injection_detected` structured events, not by matching a specific refusal sentence), a synthetic "compliance token" or real policy-leak phrase must never appear in the final assistant content, and — for the tool case — any attempted tool call must have been blocked (`tool_policy_blocked`) if the model tried it at all.

`application/live_regression_campaign.py` owns the runner (`LiveRegressionCampaignRunner`) and the gate (`require_live_campaign_gate`). The gate requires BOTH the `CONVFINQA_RUN_LIVE_SECURITY_CAMPAIGN=1` environment variable AND an explicit `--confirm` flag; either alone refuses, so the campaign cannot run as a side effect of `make test`, CI, or a normal local session. The runner:

- creates one pre-titled fixture Conversation per case (title is set via `ConversationRepository.set_title` before any LLM call, so `should_generate_title` never fires and no title-generation call is amplified onto the attack corpus);
- pins each fixture Conversation to a throwaway Document upserted through the new `SecurityCampaignFixturesPort` (`SqlAlchemySecurityCampaignFixturesRepository`), kept deliberately separate from the read-only `DocumentRepository` every other consumer relies on;
- calls the exact same `SendMessageUseCase.stream(...)` the production API uses, passing a per-call `model` override, so every selectable model in `settings.llm_models` runs the identical guardrail-wrapped code path;
- enforces a cumulative request cap and token cap (from `Finish.usage`) across the *whole* campaign (not per case), serial pacing (`asyncio.sleep` between calls, injectable for tests), and stops the entire remaining run — marking every later case/model `SKIPPED` — the moment a cap is hit or a `provider_throttled(condition=rate_limited)` signal is observed;
- deletes every fixture Conversation immediately after its case finishes (even on error, via `try/finally`) and deletes every fixture Document once the whole run completes (also via `try/finally`), regardless of pass/fail;
- judges each turn by attaching a temporary `logging.Handler` to the `convfinqa.security` logger for the duration of that one call, so pass/fail is based on which guardrail structured event fired (or didn't), never on the model's specific wording — matching the PRD's testing decision that acceptance must track application guardrail behaviour, not a provider's native refusal style;
- emits `security_regression_failed(suite="live_provider_campaign", attack_family=<category>, detail=<short reason code>)` for every failed case, and records model identity on every outcome (`LiveCampaignCaseOutcome.model`).

Run it via the CLI (never via `pytest`):

```bash
CONVFINQA_RUN_LIVE_SECURITY_CAMPAIGN=1 uv run convfinqa security campaign \
  --user-id <existing-users.id-uuid> \
  --confirm \
  --models bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0,gemini/gemini-3.5-flash \
  --request-cap 30 --token-cap 6000 --pace-seconds 2 --max-output-tokens 200
```

`--user-id` must reference an existing `users` row (the campaign does not create one, to avoid adding another cleanup surface); `--max-output-tokens` rebuilds the container's LLM adapter with that ceiling via `Settings.model_copy(update=...)`, so a single run can never emit an unbounded completion regardless of the corpus. The command exits non-zero if any case is judged `FAILED`. Interpreting results: `PASSED` means the guardrail fired when expected and no forbidden content reached the user; `FAILED` means a compliance token/policy phrase leaked or an expected block signal never fired; `SKIPPED` means a cap or rate limit stopped the campaign before that case/model pair ran — re-run with higher caps or fewer models to get full coverage, not as a silent pass.

Residual risks: the corpus is representative, not exhaustive — it does not attempt every OWASP/NIST family per category, only one or two per category, matching the acceptance criterion's "representative" framing rather than the full local regression harness. Forbidden-marker judging is a black-box heuristic; a model could in principle volunteer a poisoned table row label while answering an unrelated question and trip a false failure, or phrase a leak in a way no marker anticipates and produce a false pass — a human should read the CLI's per-case detail line, not just the final PASS/FAIL. The cost caps are best-effort empirical safeguards for an opt-in diagnostic tool, not a formal proof of bounded spend; `--max-output-tokens` bounds each call but a provider that ignores `max_tokens` on error paths could still exceed the intended budget. Follow-up: wire the campaign into an optional, manually-triggered CI job once cost ownership is agreed, and expand the corpus if a real incident reveals an attack family not yet represented here.

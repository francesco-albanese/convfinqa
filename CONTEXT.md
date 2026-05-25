# convfinqa

A conversational financial-QA system: a user pins a financial document (table + surrounding narrative), then asks multi-turn questions whose answers require looking up cells and performing simple arithmetic. The backend runs an LLM agent loop with deterministic math tools so every numeric answer is verifiable; the UI streams reasoning, tool calls, and tool results live.

## Language

### Domain corpus

**ConvFinQA dataset**:
The benchmark we serve. 3,037 train + 421 dev examples. Each example = (`doc` with `pre_text` / `post_text` / `table`, `dialogue` with `conv_questions` / `conv_answers` / `turn_program` / `executed_answers`).
_Avoid_: corpus, dataset (unqualified).

**Document**:
One ConvFinQA example's `doc` payload — narrative before the table, a single numeric/textual table, narrative after. A user "pins" one document per conversation.
_Avoid_: report, filing, file.

**Table**:
The structured part of a Document. Wire shape is `dict<column_label, dict<row_label, value>>` — outer keys are typically period labels (years), inner keys are line items (financial concepts). ~95% of cells are numeric; ~10% of tables contain at least one non-numeric cell.

**Turn program** (dataset term, read-only):
The gold sequence of operator calls that produces a dialogue turn's answer in the ConvFinQA reference. Uses a tiny DSL: `subtract(206588, 181001), divide(#0, 181001)`. We do NOT emit this DSL on the wire — it informs our tool catalog but is not user-facing.

### Conversation surface

**Conversation**:
A persistent thread of user ↔ assistant turns bound to exactly one pinned Document and one user. Identified by `conversation_id`.

**Turn**:
One user message + one assistant message within a Conversation. Has zero or more reasoning blocks, zero or more tool calls, and one final text answer.

**Pinned Document**:
The single Document the Conversation is grounded in. Pinning happens before the first turn and is currently fixed for the Conversation's lifetime.

### Agent execution

**Agent loop**:
The use-case-level driver that takes the user turn, builds an LLM request with the math + lookup tools attached, streams the response, executes any tool calls the model emits, feeds results back, and repeats until the model finishes with a text answer. Provider-agnostic (Claude Haiku 4.5, Gemini 2.5 Flash) via LiteLLM. Lives **inside** the existing `SendMessageUseCase.stream(...)` — same public `AsyncGenerator[StreamEvent]` surface, expanded event vocabulary. No new top-level use case.

**Per-tool-call SQLite**:
The lifecycle policy for the Lookup Tool's database. Every `sql_query` invocation creates a fresh `:memory:` SQLite connection, loads the pinned Document's Table rows into the Cells schema, executes the validated `SELECT`, returns rows, and discards the connection. Rebuild cost is ~1–3 ms for tables of <100 cells. No process-local cache, no cross-instance state — keeps multi-task ECS deployments correct without coordination. Document JSON in Postgres remains the single source of truth.

**Tool**:
A pure deterministic Python function the agent loop exposes to the LLM, invoked by name with JSON args, returning a JSON-serialisable result. Every tool is unit-testable in isolation. **Each Tool registers a pydantic input schema and a pydantic output schema; these schemas are the sole contract between the LLM and the tool implementation.** The system prompt may describe tools narratively for the LLM's benefit, but a tool must remain *invocable purely from its registered schema* — this is what beads epic `convfinqa-gyv` will ablation-test (remove tool docs from the system prompt, assert the LLM still calls the tools correctly via the pydantic schemas exposed in the tool-use API surface).
_Avoid_: function, action.

**Math tool**:
One of exactly five arithmetic Tools: `add`, `subtract`, `multiply`, `divide`, `greater_than`. Derived from the operator distribution in `dialogue.turn_program` across train+dev (5,131 subtract / 4,280 divide / 2,457 add / 894 multiply / 40 greater / 4 exp; the four `exp` cases do not justify a sixth tool). Internally use `decimal.Decimal` end-to-end — inputs declared as JSON `string` in the tool schema, parsed to `Decimal`, computed exactly, returned as a stringified Decimal. Avoids float drift on chained operations (no `0.1 + 0.2 → 0.30000…04`). `divide` rejects divisor `0` with an explicit error.

**Eval grader** (deferred — out of scope for the agent-architecture epic):
The future dev-set scorer that defines "exactly like `conv_answers`" as *numerically equal within displayed precision* (extract numeric value from prose, normalise to `Decimal`, compare with tolerance `0.5 × 10^-(displayed decimals)`). NOT byte-equal prose — the production response stays conversational (mockup E: "$181,001 thousand"). Designed and implemented in beads epic `convfinqa-gyv` (Evals & adversarial test harness), not in the agent-architecture epic. The agent-architecture epic ships unit tests for tools and validators only.

**Lookup tool** (`sql_query`):
The single Tool that reads from the pinned Document's Table. Signature: `sql_query(sql: str) → list[dict]`. The Table is loaded into an ephemeral in-memory SQLite database with the **Cells schema** (below). The backend strict-parses the SQL to reject anything other than a single `SELECT`, enforces a row-limit cap, and returns rows as a JSON list. **Citations fire only after the query returns at least one row** — derived from `WHERE row_label = … AND col_label = …` predicates of *successful* lookups. A `sql_query` that returns zero rows produces a `ToolResult` but no `Citation`, so the UI never points at cells that don't exist.

**Cells schema**:
The canonical SQLite layout for every Document's Table: `cells(row_label TEXT, col_label TEXT, value_num REAL NULL, value_text TEXT NULL)`. Numeric cells set `value_num`; the ~10% of cells that are non-numeric set `value_text`. The schema is identical across all Documents so the LLM only needs to learn one query shape.

**Reasoning**:
Provider-native model "thinking" surfaced by LiteLLM as `delta.reasoning_content`. Anthropic Extended Thinking and Gemini "thought summaries" both normalise to this field. The UI renders it as the numbered "reasoning · N steps" trace in mockup E. Reasoning text is **streamed live to end users** (not Anthropic's `display: "omitted"` mode) — the planning-sentence steps in mockup E (`01 scan table for 'net cash from operating activities' row`) are the reasoning text rendering. Distinct from the final visible text answer.
_Avoid_: chain-of-thought, thought (unqualified).

**Reasoning signature** (Anthropic-only):
A cryptographic token Anthropic attaches to each reasoning block on Bedrock Extended Thinking. **Sensitive — never exposed on the SSE stream.** Persisted server-side only, replayed back to the model on follow-up turns of the same Conversation. Gemini has no equivalent.

### Streaming surface

**Stream event**:
One typed payload produced by the Agent Loop and consumed by the SSE encoder. Today's events: `ConversationResolved`, `MessageStarted`, `TextDelta`, `Finish`, `ErrorEvent`, `ConcurrentRequest`. The agent epic expands this to include reasoning, tool-call, tool-result, and citation events (final vocabulary pending Question 7).

**UI Message Stream**:
The on-the-wire SSE format consumed by the frontend. Vercel AI SDK "UI Message Stream v1" framing (`type: text-delta` / `type: finish` / `type: data-*`). The Agent Loop's domain Stream Events are translated into UI Message Stream parts in `entrypoints/api/sse.py` and nowhere else.

**Sensitive payload**:
Data the backend produces but MUST NOT cross the SSE boundary to browsers. Today: the system prompt, the Anthropic reasoning signature, internal connection strings, and any raw tool error message that quotes server state (file paths, SQL execution plans). Tool input args and tool output values themselves are NOT sensitive — they're the point of the reasoning trace.

The **SSE wire** is the threat surface this rule covers. Server-to-server destinations (Langfuse SaaS via OTLP) are NOT the same surface — system prompts and reasoning signatures are forwarded there intentionally so a Trace can reconstruct a Turn. Cookies, Authorization headers, JWTs, and AWS credentials are masked before leaving the process regardless of destination (see Observability section).

### Persistence

**Message**:
One row in the `messages` table representing either a user or an assistant turn. The agent epic adds two JSONB columns: `messages.parts` and `messages.reasoning_signatures`.

**`messages.parts`** (JSONB, served to clients):
Ordered list of UIMessage-format parts, schema-versioned (`{schema_version: 1, parts: [...]}`). Each part is a discriminated union keyed by `kind`: `reasoning`, `tool_call`, `tool_result`, `citation`, `text`. Written by the Agent Loop on turn completion; read by the GET-chat-messages endpoint so the history view replays the full trace without re-running the LLM. Validated on write by a pydantic model. Size caps: reasoning block ≤16 KB, tool args ≤4 KB, tool result ≤32 KB, text answer ≤64 KB, parts array ≤256 items, total ≤256 KB per message — exceeded payloads are truncated-with-marker.

**`messages.reasoning_signatures`** (JSONB, NEVER served):
Anthropic-only. Map of `{reasoning_block_id → signature}`. Persisted so the Agent Loop can pass complete `[thinking_block, tool_use_block]` pairs back to Claude in subsequent turns of the same Conversation (Anthropic requires the signature unmodified for reasoning continuity during tool-use loops). For Gemini conversations the column is NULL. The API never reads or returns this column — it exists solely for the server-to-server multi-turn replay.

**Tool result role discipline**:
When the Agent Loop feeds a Tool Result back to the LLM, it MUST use the provider's tool-result role (Anthropic `tool_result`, OpenAI/Gemini `tool` role), NEVER `user` or `system`. LiteLLM normalises this. This is how the model distinguishes "untrusted user input" from "deterministic tool output" — collapsing them is the classical prompt-injection vector in agent loops.

### Operational invariants

**Iteration cap**:
Hard limit of 10 LLM↔tool iterations per user Turn. Dataset programs chain at most ~6 deterministic steps, so 10 is generous without being unbounded. On cap exhaustion the Agent Loop persists what it has and emits `Finish(stop_reason=ITERATION_CAP)`; the UI surfaces a "reasoning exceeded budget" chip.

**Per-tool timeout**:
`sql_query` 2 s, math tools 100 ms each. On timeout or any tool exception, the Agent Loop emits a `ToolResult(is_error=true, message=...)` back to the LLM and continues — the model is expected to self-correct (e.g. retry with a different column label). It does NOT abort the Turn.

**Code execution backend**:
Optional `python_exec(code) → stdout` tool, switched by `CODE_EXEC_BACKEND=disabled | agentcore | lambda`. Default `disabled`; the deterministic Math Tool catalog covers 99.97% of the dataset (ADR-0005). When enabled, AgentCore is the AWS-managed option (Firecracker microVM, per-session); Lambda is the DIY locked-execution-role option. Not in scope for the agent-architecture epic; tracked in beads epic `convfinqa-gyv`.

### Observability

**Trace**:
One user Turn's end-to-end execution in Langfuse, rooted at the FastAPI request span (`POST /api/v1/chat/stream`). Contains nested Observations: one Agent span, 1–10 Generations, zero-or-more Tool spans. Identified by an OpenTelemetry trace_id. A Conversation produces one Trace per Turn.

**Observation**:
Langfuse umbrella term for any timed unit inside a Trace. The types we use: `span`, `generation`, `agent`, `tool`. Other Langfuse-defined types (`event`, `chain`, `retriever`, `evaluator`, `embedding`, `guardrail`) are not used today.

**Generation**:
Langfuse Observation type for one `litellm.acompletion(...)` call. Emitted automatically by the LiteLLM `langfuse_otel` callback. Carries model, full input messages, assembled output (text + reasoning + tool_calls), token usage, finish_reason, latency, time-to-first-token. One Turn produces 1–10 Generations (one per agent-loop iteration, bounded by `ITERATION_CAP`).

**Tool span**:
Langfuse Observation of type `tool` wrapping one math or `sql_query` invocation inside the agent loop. Input = parsed tool args; output = tool result (Decimal string for math, `list[dict]` for sql_query, or the error message on tool failure).

**Agent span**:
Langfuse Observation of type `agent` wrapping the body of `SendMessageUseCase.stream(...)`. Carries `trace_user_id` (= `users.id`), `session_id` (= `conversation_id`), and trace-level metadata (document_id, llm_model, stop_reason, total tokens, total cost). Parent of all Generations and Tool spans in the Trace.

**Session** (Langfuse):
Langfuse grouping that collects all Traces sharing a `session_id`. We bind `session_id = conversation_id`, so one Conversation = one Langfuse Session = N Traces (one per Turn).

**trace_user_id**:
Langfuse field that joins all of a user's Traces across all Sessions. Bound to `users.id` (UUID), resolved by auth middleware from `cognito_sub`. NOT email, NOT cognito_sub — keeps Langfuse free of Cognito-specific identifiers and PII.

## Flagged ambiguities

**"reasoning step" (mockup language) vs Reasoning (backend term)**:
Mockup E shows numbered steps like `01 scan table…`, `02 table.lookup(...) → 206588`, `03 convert to a human-readable figure`. These "steps" are NOT raw Reasoning text — they're a *rendering* of an interleaved sequence of Reasoning fragments AND Tool Call invocations. The backend emits the underlying events; the UI composes them into the numbered step list. The word "step" therefore has no backend equivalent — do not introduce a `Step` event type.

**"thinking…" (mockup language)**:
Cosmetic label the UI shows while a Reasoning block is still streaming. Not a distinct backend concept.

## Documented decisions

- [ADR-0001](docs/adr/0001-agent-loop-inside-send-message-usecase.md) — Agent Loop lives inside `SendMessageUseCase`, not a separate use case
- [ADR-0002](docs/adr/0002-sql-per-document-store.md) — Per-document SQL store via ephemeral `:memory:` SQLite + `sql_query` tool
- [ADR-0003](docs/adr/0003-math-tool-catalog-decimal.md) — 5-tool math catalog (`add/subtract/multiply/divide/greater_than`) with Decimal end-to-end, derived from dataset operator distribution
- [ADR-0004](docs/adr/0004-persistence-parts-and-reasoning-signatures.md) — Two-column trace persistence: `messages.parts` JSONB (served) + `messages.reasoning_signatures` JSONB (server-only)
- [ADR-0005](docs/adr/0005-sandboxed-code-exec-deferred.md) — Sandboxed code execution deferred behind `CODE_EXEC_BACKEND=disabled` flag stub
- [ADR-0006](docs/adr/0006-prompts-and-tool-docs-split.md) — System prompt and tool docs are separate modules; Tools invocable from pydantic schemas alone
- [ADR-0007](docs/adr/0007-observability-langfuse-and-application-signals.md) — Observability: Langfuse 4.x for LLM + CloudWatch Application Signals via ADOT sidecar for infra, dual-export through a single OTel TracerProvider; manual context-manager spans in the use case (not `@observe`) because of async-generator + StreamingResponse bugs

Follow-up work tracked in beads epic [`convfinqa-gyv`](#) — evals & adversarial test harness.

## Example dialogue

> Dev: "When the LLM does `subtract(206588, 181001)`, is that a Reasoning step?"
>
> Domain expert: "No — that's a Tool Call, specifically a Math Tool invocation. Reasoning is the model's narrative thinking, which on this stream might be the words 'I need to subtract 2008 from 2009' that *led* to the Tool Call. They're separate Stream Events; the UI happens to render them in one numbered list."
>
> Dev: "So the cited row/col chip in the mockup — where does that come from?"
>
> Domain expert: "It's a side-effect of the Lookup Tool. When the agent calls the Lookup Tool to fetch a cell, the args (row label, column label) become the citation. No Lookup Tool call = no citation. We don't author citations independently."
>
> Dev: "And if I'm running Gemini instead of Claude, do I lose anything?"
>
> Domain expert: "You lose the Reasoning Signature, which the user never sees anyway. Reasoning content itself comes through normalised on `delta.reasoning_content` for both providers. The Agent Loop, the Tool catalog, the Stream Event vocabulary — all identical."

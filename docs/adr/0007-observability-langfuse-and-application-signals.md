# Observability: Langfuse 4.x for LLM + CloudWatch Application Signals via ADOT sidecar for infra, sharing one OTel TracerProvider

Date: 25-05-2026

## Context

`docs/aws-architecture.md` §3.9 originally chose CloudWatch Logs + ALB access logs only, with Langfuse SaaS as a future-tense LLM signal. The package pin (`langfuse>=4.5.1`) shipped without instrumentation. The user now wants:

1. End-to-end reconstruction of one Turn in Langfuse — question, system prompt, full wire history per iteration, reasoning, tool calls (args + results), assembled LLM outputs, tokens, USD cost, latency, stop reason.
2. OpenTelemetry observability for the AWS core services (FastAPI, SQLAlchemy, asyncpg, httpx, botocore, Lambda BFF) so AWS-side issues (slow Aurora query, throttled Bedrock, JWKS fetch fail, JWT validation error) are debuggable in a service map.
3. Same Trace shape whether a Turn is driven by the CLI (`convfinqa chat`) or the SPA — both go through `POST /api/v1/chat/stream`, so there is one code path to instrument.
4. Single Langfuse project for all environments, differentiated by `environment` tag; tests are observability no-ops.

Langfuse 4.x is a thin wrapper over the official OpenTelemetry Python SDK and accepts OTLP/HTTP at `/api/public/otel`. By default the `LangfuseSpanProcessor` filters spans server-side, exporting only LLM-flavored ones (`gen_ai.*` attributes, Langfuse SDK spans, known LLM instrumentors) — infra spans are dropped *from Langfuse* but a second `BatchSpanProcessor` attached to the same `TracerProvider` sees everything.

Two Langfuse bugs make `@observe` the wrong primitive for our shape:
- [#7226](https://github.com/langfuse/langfuse/issues/7226) — `@observe` on `async def f() -> AsyncGenerator` records `<async_generator>` as the output. `SendMessageUseCase.stream(...)` is exactly this shape.
- [#8216](https://github.com/langfuse/langfuse/issues/8216) — `@observe` + `FastAPI StreamingResponse` fragments traces into disconnected pieces.

## Decision

**Single OpenTelemetry `TracerProvider`, two span processors, three signal types:**

1. `LangfuseSpanProcessor` — exports LLM-flavored spans to `https://cloud.langfuse.com/api/public/otel` (Basic auth, `x-langfuse-ingestion-version: 4`).
2. `BatchSpanProcessor` with OTLP exporter to the in-task ADOT Collector sidecar (`http://localhost:4317`) — exports *every* span (LLM + infra) onward to CloudWatch Application Signals.

**FastAPI auto-instrumentation owns the root span.** Every `/api/v1/*` and `/api/auth/*` request opens an HTTP-server span via `opentelemetry-instrumentation-fastapi`. Everything else nests under it via W3C trace-context propagation.

**Inside `SendMessageUseCase.stream(...)`:**
- One outer `langfuse.start_as_current_observation(as_type="agent", name="send_message")` context manager carrying `trace_user_id = users.id`, `session_id = conversation_id`, plus `document_id`, `llm_model`, and (post-loop) `stop_reason` / total tokens / total USD cost in trace metadata.
- LiteLLM `langfuse_otel` callback (`litellm.callbacks = ["langfuse_otel"]`) auto-emits one `generation` Observation per `litellm.acompletion(...)` call. It joins the active OTel context via propagation, so the generation appears as a child of the agent span. USD cost is attached via a sibling LiteLLM `success_callback` that fires in the same async context where the just-emitted generation span is still resolvable as the current OTel observation; it calls `langfuse.update_current_generation(cost_details=litellm.completion_cost(model=..., completion_response=...))`. The callback path is the load-bearing detail — computing cost post-stream from outside the callback would race the OTel span finalisation.
- Each tool execution in `agent/tool_executor.py` is wrapped in `langfuse.start_as_current_observation(as_type="tool", name=tool_name)` with input/output captured explicitly.

**No `@observe` decorators.** All Langfuse instrumentation is manual `start_as_current_observation` context managers — sidesteps the two bugs above.

**Auto-instrumentations enabled in the FastAPI process:** `opentelemetry-instrumentation-fastapi`, `-sqlalchemy`, `-asyncpg`, `-httpx`, `-botocore`, `-logging` (injects trace_id/span_id into Python log records → CloudWatch Logs Insights can join logs to traces), `system_metrics` (process CPU/memory).

**Cost source.** `litellm.completion_cost(model=..., completion_response=...)` is the source of truth for USD cost. Langfuse-side custom-model definitions are NOT used (avoids two sources of truth for prices).

**Masking.** A global Langfuse `mask=` function redacts Cookies, Authorization headers, JWT-shape strings (3 dot-separated base64 segments), and keys matching `/secret|password|token|api_key|aws_session|aws_access/i`. FastAPI instrumentation is configured with header filtering so cookies never enter span attributes upstream of the mask. Everything else — user_text, tool args, tool results, system prompt, reasoning signatures, full wire history — flows.

**ADOT sidecar.** ECS Express Mode task gains a second container (`public.ecr.aws/cloudwatch-agent/cloudwatch-agent:latest`) listening on `localhost:4317`. Hard memory budget 64 MB, soft 32 MB. The task size stays at 0.5 GB / 0.25 vCPU — we do NOT bump to 1 GB. The sidecar is capacity-constrained on purpose; if it OOMs, App Signals itself surfaces it and the LangfuseSpanProcessor (which exports independently of the sidecar) keeps LLM observability intact. Task IAM role grants `CloudWatchAgentServerPolicy`. ADOT Collector config = AWS standard sample for App Signals only (no extra EMF logs exporter — CloudWatch Logs already receives app stdout via the `awslogs` driver).

**Auth BFF (TypeScript Lambda).** ADOT Node.js managed Lambda layer attached to all five functions (`login`, `callback`, `refresh`, `logout`, `post-confirmation`). Sink: same CloudWatch Application Signals. Cold-start hit (~100–300 ms from the layer) is accepted — `login` / `callback` / `refresh` / `logout` are called once per session; `post-confirmation` runs inside Cognito's 5 s timeout with margin to spare.

**Identity & session binding.**
- `trace_user_id` = `users.id` UUID (NOT `cognito_sub`, NOT email).
- `session_id` = `conversation_id`.
- A Turn that pre-dates user resolution (validation failure, anon endpoints) emits a Trace without `trace_user_id`.

**Operational defaults.** 100% head sampling; `BatchSpanProcessor` with 5s flush; on OTLP unreachable, drop the batch after default retries (app never blocks); `langfuse.flush()` invoked on FastAPI lifespan shutdown and Lambda handler exit.

**Environment separation.** Single Langfuse project across all environments, tagged via the `environment` trace attribute (`prod` / `dev`). Tests set `LANGFUSE_ENABLED=false` so SDK init becomes a no-op; the OTLP exporter to ADOT is also disabled in test config.

**Langfuse pin.** `langfuse==4.6.1` (released 2026-05-08). Verified against the release notes for 4.5.0 → 4.6.1: no breaking changes to `start_as_current_observation`, the `langfuse_otel` callback, the `mask=` constructor argument, `propagate_attributes()`, or `cost_details` / `usage_details` on `update_current_generation`. The 4.5.0 `fix(observe): preserve streaming context` line is irrelevant here because we don't use `@observe`.

## Considered and rejected

- **`@observe` decorators on use case + tools.** Hits Langfuse #7226 (async generator → `<async_generator>` as output) and #8216 (FastAPI `StreamingResponse` → fragmented traces). Both bugs apply to `SendMessageUseCase.stream(...)` directly.
- **Send infra spans to Langfuse too (no AWS sink).** The Langfuse UI is LLM-centric; a SQLAlchemy `SELECT` span in the Sessions view is alien. Mixes operational and product signal in a tool that isn't built for the former.
- **X-Ray only (no Application Signals).** Saves nothing at portfolio scale ($0.000005/trace vs free 100M signals/mo) and loses the service map + SLO UX. Application Signals is built on X-Ray + CloudWatch Metrics under the hood.
- **CloudWatch Logs only (status quo from §3.9).** Doesn't satisfy the "full OpenTelemetry observability for core services" requirement.
- **Define custom Bedrock models in the Langfuse UI for cost.** Adds a second source of truth (Langfuse UI prices vs LiteLLM's `completion_cost` table) — when the two drift, the per-call cost in the Trace UI doesn't match what `litellm.completion_cost` returns programmatically.
- **Per-streaming-delta spans (one span per text/reasoning/tool-arg delta).** Trace size explodes (100–1000 spans per Turn); Langfuse UI becomes unreadable; near-zero analytical value over assembled output.
- **Separate Langfuse projects per environment.** User preferred a single tagged project. Acknowledged trade-off: prod dashboards average over local dev experiments.
- **Tail-based sampling via standalone OTel Collector.** Premature at portfolio scale — adds a Collector deployment for no current cost pressure.
- **Tests emit traces tagged `environment: test`.** Would burst the Langfuse Hobby observation cap in days for synthetic signal of dubious value.

## Consequences

`docs/aws-architecture.md` §3.9 is rewritten to reflect the dual-sink architecture; its cost line moves from "$0" to "~$0 within free tiers" (Application Signals free tier 100M signals/mo, Langfuse Hobby free tier 50K obs/mo — both comfortably above portfolio traffic). The "No X-Ray, no Container Insights" cost invariant in §1 is preserved (Application Signals is not Container Insights and supersedes our X-Ray need).

New files at composition time:
- `backend/src/convfinqa/adapters/observability/` — `tracer_provider.py` (single TracerProvider factory with both processors), `mask.py` (global Langfuse mask function), `instrumentation.py` (auto-instrumentation registration).
- `backend/src/convfinqa/container/bootstrap.py` — initializes the TracerProvider before any adapter is constructed; registers auto-instrumentations once.
- `backend/src/convfinqa/application/agent/iteration.py` and `tool_executor.py` — wrap the LLM iteration loop and per-tool execution in `start_as_current_observation` context managers.
- `backend/src/convfinqa/adapters/llm/litellm_adapter.py` — enables `litellm.callbacks = ["langfuse_otel"]` at import; on stream completion, calls `langfuse.update_current_generation(cost_details=...)` from `litellm.completion_cost(...)`.
- `terraform/environmental/modules/compute/` — ECS task definition gains the CloudWatch-agent sidecar container (memory hard 64 MB / soft 32 MB); task IAM role gets `CloudWatchAgentServerPolicy`. Task size stays 0.5 GB / 0.25 vCPU; sidecar OOMs (if they occur) surface in App Signals itself, and the LangfuseSpanProcessor exports independently so LLM observability is unaffected.
- `terraform/environmental/modules/compute/` (auth-lambda) — each of the five Lambda functions gets the ADOT Node.js managed layer ARN; execution role gets `AWSXRayDaemonWriteAccess` + `CloudWatchLambdaApplicationSignalsExecutionRolePolicy`.
- `.env.example` / SSM Parameter Store — new keys: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (defaults to EU), `LANGFUSE_ENABLED` (default `true`; tests set `false`), `OTEL_SERVICE_NAME=convfinqa`, `OTEL_RESOURCE_ATTRIBUTES=environment=$ENV`.
- Test config (`backend/tests/conftest.py` or equivalent) — sets `LANGFUSE_ENABLED=false` and stubs the TracerProvider with a no-op exporter so spans never leave the test process.

The CLI (`convfinqa chat`) is unchanged — it hits the FastAPI endpoint, so its Traces are identical to the SPA's by construction. There is no client-side observability to wire.

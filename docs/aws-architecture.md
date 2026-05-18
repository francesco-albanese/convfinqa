# convfinqa — AWS Architecture & Decisions

Canonical reference for how the convfinqa portfolio app is deployed to AWS: stack choice, decision lineage, runtime flows, disqualified alternatives, operational runbook. Designed to be re-read on demand by both the author and AI agents that touch infrastructure.

- **Status**: design approved, not yet implemented
- **Project**: convfinqa portfolio
- **Reference repo**: `../francescoalbanese-dev-infra`
- **Diagrams**: see [`aws-architecture.html`](./aws-architecture.html) for rendered Mermaid sequence/flow diagrams (top-level architecture, sign-up/sign-in flows, streaming chat, Aurora cold-start, lifecycle, CI/CD job graph).

---

## 1. Executive summary & cost

The convfinqa app is a streaming LLM-powered financial QA SPA. It runs on AWS with cost as the dominant constraint and a "tear it down between showings" lifecycle.

### The stack in one paragraph

A React/Vite SPA served from **S3 behind a single CloudFront distribution**. The same CloudFront domain (`app.convfinqa.francescoalbanese.dev`) routes `/api/v1/*` to a **FastAPI service on ECS Express Mode** (Fargate-backed, auto-wired ALB) and `/api/auth/*` to a **TypeScript Lambda BFF** that handles the Cognito + Google OAuth flow and sets HTTPOnly + Secure cookies. Persistence is **Aurora Serverless v2 (Postgres-compatible) scaled to 0 ACU when idle**; cache, rate-limit, and idempotency live in the same Aurora cluster as Postgres tables. Secrets are in **SSM Parameter Store**. DNS records are written by convfinqa terraform via a cross-account provider into the parent `francescoalbanese.dev` zone owned by `../francescoalbanese-dev-infra`. Everything is one Terraform stack split into modules so that `terraform destroy -target=module.compute` drops the monthly cost to ~$1-2 when not actively shown.

### Cost at a glance

| Scenario | Monthly cost | Detail |
| --- | --- | --- |
| Idle, full stack up | ~$28-32 | ALB dominates (~$16). Fargate baseline task ~$10. Aurora paused storage ~pennies. CloudFront/S3/Route53/Lambda BFF ~$0 idle. |
| "Going on holiday" (compute destroyed) | ~$1-2 | Aurora paused storage (~$0.05/GB-mo) + S3 site bucket (~$0.50/mo) + ACM cert (free) + Route53 zone (free, shared). CloudFront only pays on request. |
| Project fully destroyed | ~$0 | All resources removed. DNS records vanish, ACM cert revoked, S3 emptied. Domain registration handled out-of-band by Porkbun. |

### Hard cost invariants

- No EKS — `$72/mo control plane` alone is a disqualifier.
- No NAT Gateway — `~$32/mo`. We use public-subnet Fargate locked to the CloudFront origin prefix list instead.
- No ElastiCache (~$11/mo floor) or DynamoDB until measurement proves the need.
- No Secrets Manager ($0.40/secret/mo) — SSM Parameter Store SecureString is free.
- No CloudFront Container Insights, no X-Ray, no WAF — cost-priority defaults off.

---

## 2. System architecture (text form)

> The Mermaid flowchart for this section lives in [`aws-architecture.html`](./aws-architecture.html#architecture-diagram). Plain-text equivalent below for agents that cannot render Mermaid.

Single-domain CloudFront edge fans out to three origins by path. HTTPOnly cookies set by the Lambda BFF travel automatically to the FastAPI origin because both share the same hostname.

1. The browser hits a single hostname (`app.convfinqa.francescoalbanese.dev`). CloudFront terminates TLS using a SAN ACM cert.
2. CloudFront routes by path: `/*` goes to a private S3 bucket via Origin Access Control (the SPA bundle), `/api/auth/*` goes to a Lambda Function URL (TypeScript BFF for auth), `/api/v1/*` goes to an ALB auto-wired by ECS Express Mode.
3. The ALB forwards to a Fargate task running FastAPI + uvicorn (the convfinqa container).
4. FastAPI reads/writes Aurora Serverless v2 (Postgres-compatible). Aurora hosts the business tables (users, conversations, messages, documents) *and* the cache/rate-limit/idempotency tables.
5. FastAPI calls Bedrock for LLM inference, reads secrets from SSM, and emits traces to Langfuse SaaS (external).
6. The Lambda BFF orchestrates the Cognito OAuth flow with Google, sets HTTPOnly + Secure + SameSite=Lax cookies for `access_token` and `refresh_token`, and performs a defensive `INSERT ON CONFLICT DO NOTHING` into the `users` table.
7. A Post-Confirmation Lambda Trigger (Cognito-invoked, no Function URL) creates the `users` row when Cognito confirms a new identity. The BFF UPSERT is a fallback if this trigger fails.
8. A keep-alive Lambda fired by EventBridge every ~20 hours runs `SELECT 1` against Aurora to prevent it from entering the >24h "deep sleep" state that doubles resume latency.

---

## 3. Architectural decisions

Every load-bearing choice with its one-line lineage (the punchline), what we chose, and what we explicitly rejected. The full alternative comparison lives in [section 5](#5-disqualified-alternatives).

### 3.1 Backend compute decision

**Status**: Decided · **Cost**: ~$26-30/mo idle

**Lineage:** Chose ECS Express Mode after EKS ($72/mo control plane), App Runner (sunset 2026-04-30), API Gateway (HTTP API can't stream; REST API has no Cognito authorizer), Lambda Web Adapter (not the user's preferred "production AI streaming" optic), and hand-wired Fargate (same cost, more Terraform).

**Chose:** `ECS Express Mode` (the re:Invent 2025 deployment mode that auto-wires Fargate + ALB + cert + scaling + networking). Backed by Fargate; one on-demand baseline task; capacity provider strategy for cost.

**Why this won**
- Same cost floor as hand-wired Fargate (~$26-30/mo, ALB ~$16 dominates) with far less Terraform — AWS auto-wires the LB, cert, autoscaling, networking.
- Public-subnet Fargate with security group locked to the `com.amazonaws.global.cloudfront.origin-facing` prefix list — avoids the silent **$32/mo NAT Gateway** or **$22/mo VPC interface endpoints** tax.
- SSE / long-lived HTTP response streaming works natively (Fargate is just a long-lived process).
- Shares the ALB across multiple Express Mode services if more portfolio apps land on the same network config later.
- Cognito offload could later move onto the ALB if the BFF pattern is dropped (we are NOT doing that — see [routing decision](#34-edge--routing-decision)).

**Implementation notes**
- Capacity provider strategy: 1 Fargate on-demand baseline, room for Fargate Spot extras when autoscaling kicks in. Spot is NOT used for the baseline — AWS guidance explicitly excludes user-facing services.
- Task size: 0.25 vCPU / 0.5 GB. Minimum Fargate tier.
- Container image stored in ECR private repo, built on every merge to main, tagged with git SHA.

> **Gotcha:** ECS Express Mode cannot scale to zero with an ALB attached. The "scale to zero" lever is `terraform destroy -target=module.compute`, not autoscaling.

### 3.2 Database decision

**Status**: Decided · **Cost**: ~$0/mo idle (storage only)

**Lineage:** Chose Aurora Serverless v2 min 0 ACU (true scale-to-zero, AWS-native) after rejecting RDS db.t4g.micro ($12-14/mo always-on), Aurora min 0.5 ACU ($43/mo), and Neon (off-AWS — breaks the all-AWS narrative). The 15-30s cold-start UX hit is accepted in exchange for ~$0 idle cost.

**Chose:** `Aurora Serverless v2 (Postgres-compatible)`, min 0 ACU, max ~2 ACU. Auto-pause after configurable idle window (5min–24h).

**Verified resume-latency facts (AWS docs, Nov 2024 GA)**
- Resume "up to 15 seconds" for clusters paused less than 24h.
- **30+ seconds for "deep sleep"** after >24h paused.
- Won't auto-pause if any user connection is open, RDS Proxy is attached, binlog replication is on, global database primary, or Zero-ETL active.
- Storage cost when paused: `$0.10/GB-month`.

**Four mandatory mitigations (the cost saving only materialises with ALL four)**
1. **Keep-alive Lambda on EventBridge cron**, every ~20h, runs `SELECT 1`. Keeps the cluster out of deep sleep so resume stays at ~15s rather than 30s+. Cost: ~$0.04/mo.
2. **SQLAlchemy pool tuning**: `pool_recycle=300`, `pool_size=2`, `max_overflow=2`, `pool_pre_ping=True`. Without this, the pool keeps connections persistent and Aurora *never* pauses.
3. **NO RDS Proxy**. It pins connections and blocks auto-pause.
4. **Frontend "waking up..." loader** + SPA-on-mount fetch to `/api/v1/healthz` to warm the DB while the user reads the page, before they click Send.

> **Code gotcha (verified):** `backend/src/convfinqa/adapters/persistence/sqlalchemy/engine.py` today calls `create_async_engine(database_url, pool_pre_ping=True, future=True)` — SQLAlchemy's default `pool_recycle=-1` means connections are *never* recycled. Aurora will not pause under this config. Fix is required when Aurora is provisioned.

**Why this won**
- True scale-to-zero. Compute portion of DB cost is exactly $0 during idle hours.
- Postgres-compatible — no app or alembic changes vs current docker-compose Postgres 18.
- Stays inside AWS — preserves the all-AWS portfolio narrative.
- `asyncpg` connect/SSL timeouts already default well above the 15s resume window.

> **Caveat:** The first click after >24h idle without keep-alive working will hang ~30s. This is the explicit UX trade-off the user accepted in exchange for zero idle cost.

### 3.3 Frontend hosting decision

**Status**: Decided · **Cost**: ~$0.50/mo

**Lineage:** Mirror `../francescoalbanese-dev-infra` exactly — that pattern is proven, audited, and reusable. No need to invent.

**Chose:** Private S3 bucket behind CloudFront with OAC. ACM cert in `us-east-1`. `PriceClass_100`. Dual-tier cache. SPA fallback. No WAF.

**Components**
- **S3 bucket**: `convfinqa-site-<account_id>`, versioned, encrypted SSE-S3, public access blocked, accessed only via CloudFront OAC.
- **CloudFront distribution**: aliases `app.convfinqa.francescoalbanese.dev` + `convfinqa.francescoalbanese.dev`; PriceClass_100 (NA + EU edges only).
- **ACM cert**: us-east-1 (CloudFront requirement), single SAN over both names, DNS-validated.
- **Cache policies**: 1-year immutable for `/_assets/*` and `/assets/*` (hashed); 5-min TTL for `/` and `/index.html`.
- **SPA routing**: 403 and 404 from S3 are rewritten to `/index.html` with HTTP 200 — the canonical SPA pattern.
- **Security headers policy**: HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy strict-origin-when-cross-origin.
- **No WAF**. Acceptable for portfolio risk profile; revisit if abuse surfaces.

**Additional CloudFront behaviors layered on top (auth-aware routing)**

| Path pattern | Origin | Cache policy | Origin request policy |
| --- | --- | --- | --- |
| `/api/v1/*` | ALB (ECS Express) | `Managed-CachingDisabled` | `Managed-AllViewer` |
| `/api/auth/*` | Lambda Function URL (BFF) | `Managed-CachingDisabled` | `Managed-AllViewer` |
| `/*` | S3 (SPA) | Dual-tier (1y / 5min) | None (default) |

### 3.4 Edge / routing decision

**Status**: Decided

**Lineage:** Single CloudFront domain with path-based routing keeps HTTPOnly cookies same-origin — no CORS, no cross-subdomain cookie loss. Rejected ALB's built-in Cognito auth because its opaque session cookie cannot expose the raw Cognito tokens the BFF needs.

**Chose:** One hostname (`app.convfinqa.francescoalbanese.dev`), three CloudFront behaviors fan out to three origins. Auth and API share the cookie jar because they share the domain.

**Why same-origin matters**

The Lambda BFF sets `Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Lax` on `app.convfinqa.francescoalbanese.dev`. Because `/api/v1/*` lives on the same domain, the browser attaches that cookie automatically on every backend call. No CORS preflight, no `document.cookie` exposure, no cross-subdomain refresh handshake.

**Why not ALB's built-in Cognito authentication**

ALB can authenticate users against a Cognito User Pool natively (it sets `AWSELBAuthSessionCookie`). The cookie is HTTPOnly and Secure — sounds perfect. But it is **opaque**: the app cannot read the underlying Cognito `access_token` or `refresh_token` from it. The user's requirement is "store the *real* Cognito tokens server-side in HTTPOnly cookies so they are readable on the server" → ALB auth is incompatible with that requirement. The Lambda BFF pattern is the only way.

### 3.5 Cache & rate-limit decision

**Status**: Decided · **Cost**: $0 (reuses Aurora)

**Lineage:** Chose Postgres tables in the same Aurora cluster over DynamoDB and Redis because at portfolio LLM-streaming scale, sub-ms vs single-digit-ms cache hits are invisible against multi-second model calls — and Postgres is already in docker-compose for dev parity.

**Chose:** Three Postgres tables in the same Aurora cluster — `rate_limit`, `output_cache`, `idempotency_keys` — accessed via hexagonal ports `CachePort` and `RateLimitPort` so a future swap to DynamoDB or Redis is a single-adapter change.

**Patterns**
- **Rate-limit** — atomic increment via UPSERT:
  `INSERT INTO rate_limit (user_id, window_start, count) VALUES ($1, $2, 1) ON CONFLICT (user_id, window_start) DO UPDATE SET count = rate_limit.count + 1 RETURNING count;`
  ~1 ms on indexed table at portfolio scale.
- **Output cache** — `(prompt_hash, model, response, expires_at)` with a partial index on non-expired rows. Query-time `WHERE expires_at > now()` filter.
- **Idempotency keys** — same pattern; expiry typically 24h.
- **Aggressive prompt caching** against Bedrock is a *request-side* feature (LiteLLM passes `cache_control` markers through to Bedrock). It needs **zero infrastructure**.

**Why not DynamoDB or Redis**
- Latency win invisible against multi-second LLM calls.
- ElastiCache cheapest tier is ~$11/mo; ElastiCache Serverless ~$70/mo floor.
- DynamoDB requires a second service in docker-compose (DynamoDB Local). LocalStack archived its public repo on 2026-03-23 — alternatives exist (MiniStack, Floci, Moto) but they're added complexity.
- Same Aurora cluster + same alembic = one DB to back up, one to restore, one to migrate.

### 3.6 Secrets decision

**Status**: Decided · **Cost**: Free

**Lineage:** Chose SSM Parameter Store SecureString over Secrets Manager because rotation isn't a portfolio requirement and Secrets Manager's $0.40/secret/mo is avoidable.

**Chose:** SSM Parameter Store, `SecureString` type, AWS-managed KMS key. Standard tier (4 KB max per parameter) is free.

**Parameter path layout**
```
/convfinqa/<env>/database_url
/convfinqa/<env>/bedrock_region
/convfinqa/<env>/cognito_user_pool_id
/convfinqa/<env>/cognito_client_id
/convfinqa/<env>/cognito_client_secret
/convfinqa/<env>/system_prompt_override   (optional)
```

ECS task role + Lambda execution role get scoped `ssm:GetParameters` on `arn:aws:ssm:<region>:<account>:parameter/convfinqa/<env>/*` and `kms:Decrypt` on the AWS-managed key for SSM.

Upgrade path: move to Secrets Manager when DB credential rotation becomes a real requirement (post-portfolio).

### 3.7 DNS / TLS decision

**Status**: Decided · **Cost**: ~$0

**Lineage:** Chose Pattern Y — convfinqa terraform writes records into the parent zone via cross-account provider — because it keeps each repo's apply independent and avoids the two-step "convfinqa creates pending cert / dev-infra writes validation / convfinqa finalises" dance.

**Chose:**
- Parent zone `francescoalbanese.dev` stays in the shared-services account, as a *data source* in the dev-infra repo (it was originally created by a prior mTLS project).
- **No new hosted zone in the convfinqa account.** All records live in the parent zone.
- ACM cert in `us-east-1`: single SAN over `app.convfinqa.francescoalbanese.dev` + `convfinqa.francescoalbanese.dev`. DNS-validated.
- convfinqa terraform declares an `aws.shared_services` provider alias that assumes a scoped IAM role with `route53:ChangeResourceRecordSets` on records matching `*.convfinqa.francescoalbanese.dev` only.
- convfinqa terraform creates: ACM validation CNAMEs, alias `A` + `AAAA` records for `app.convfinqa.francescoalbanese.dev` → CloudFront.
- dev-infra is untouched after the one-time IAM role creation.

**Cognito redirect URI**

`https://app.convfinqa.francescoalbanese.dev/api/auth/callback` — handled by the BFF Lambda. Must be configured in both the Cognito User Pool and the Google OAuth client.

### 3.8 Tear-down ergonomics decision

**Status**: Decided

**Lineage:** Single Terraform stack split into modules so `terraform destroy -target=module.compute` drops the cost to ~$1-2/mo without losing data, certs, or DNS.

**Chose:** One stack `terraform/environmental/`, internally modularised. Module-level destroy targets map to lifecycle classes.

| Module | Lifecycle | What's inside | Idle cost |
| --- | --- | --- | --- |
| `modules/network/` | Long-lived | VPC, subnets, SGs | $0 |
| `modules/data/` | Long-lived | Aurora Serverless v2 cluster | ~$0.05/GB storage |
| `modules/edge/` | Long-lived | CloudFront, S3 site bucket, ACM cert, Route53 records | ~$0.50 |
| `modules/compute/` | **Ephemeral** | ECS Express service, ALB, Lambda BFF + zip, SSM params, Cognito User Pool | ~$26-30 |
| `modules/keepalive/` | Ephemeral | EventBridge cron + Lambda that pings Aurora | ~$0.04 |

**The three tear-down levers**
- **Going on holiday**: `terraform destroy -target=module.compute -target=module.keepalive`. Cost ≈ $1-2/mo.
- **Coming back**: `terraform apply`. ECS Express auto-wires ALB+task; live in ~5 min.
- **Project dead**: full `terraform destroy`. Take an Aurora snapshot first if data matters.

### 3.9 Observability decision

**Status**: Decided · **Cost**: ~$0 (within free tier)

**Lineage:** CloudWatch with cheap defaults handles infrastructure; Langfuse SaaS handles the LLM-specific signal. Skip Container Insights, X-Ray, and CloudFront response logs — all paid features that don't earn their cost at portfolio scale.

**Chose:**
- **CloudWatch Logs**: 7-day retention; JSON-structured (the FastAPI app already uses `python-json-logger`). Free tier covers our volume.
- **Container Insights OFF** (saves ~$0.50/mo per container).
- **ALB access logs** to a small S3 bucket with a 30-day lifecycle policy. Recommended over CloudFront response logs (cheaper, contains the same data plus client IP after CloudFront forwards).
- **No CloudWatch dashboards.**
- **No X-Ray.**
- **Langfuse SaaS** for LLM tracing — already wired via the project's `langfuse-trace` skill. Free tier sufficient.

### 3.10 CI/CD decision

**Status**: Decided

**Lineage:** One GitHub Actions workflow with path-filtered jobs. Migrations run as a one-shot Fargate task *before* the service update so a bad migration blocks the deploy instead of half-applying.

**Chose:** Single workflow `.github/workflows/deploy.yml`, GitHub OIDC into the existing IAM deploy role, jobs gated by path-filter.

**Job topology**

| Job | Trigger | What it does |
| --- | --- | --- |
| `terraform-plan` | PR touching `terraform/**` | Validates + plans; comments the plan on the PR. |
| `terraform-apply` | Push to main, if `terraform/**` changed | Applies. Cross-account state assume via existing OIDC role. |
| `migrations` | After `terraform-apply`, if `backend/alembic/**` or persistence code changed | `aws ecs run-task` launches a one-shot Fargate task running `alembic upgrade head`. Failure blocks downstream. |
| `backend-deploy` | After `migrations`, if `backend/**` changed | Docker build → ECR push (tag = git SHA) → `aws ecs update-service`. Rolling deploy: 200% max, 50% min. |
| `frontend-deploy` | Parallel; `frontend/**` changed | `pnpm install` + `pnpm build` → `aws s3 sync` → CloudFront invalidate `/index.html` and `/`. |
| `auth-lambda-deploy` | `auth-lambda/**` changed | `pnpm install` + esbuild → `aws lambda update-function-code` for all five functions. |
| `compute-destroy` | `workflow_dispatch` only | Runs `terraform destroy -target=module.compute -target=module.keepalive`. The "go on holiday" button. |

### 3.11 API URL convention decision

**Status**: Decided

**Lineage:** Rename FastAPI router prefix from `/v1/*` to `/api/v1/*`. Same-domain SPA + API needs an unambiguous prefix so client-side SPA routes (`/login`, `/chat/abc`) can never collide with backend paths.

**Chose:** All backend endpoints under `/api/v1/*`; all auth-BFF endpoints under `/api/auth/*`; everything else is SPA. Standard 2026 pattern for same-domain SPA+API apps.

**Mechanical changes required**
- FastAPI router prefix: `app.include_router(router, prefix="/api/v1")`.
- Frontend API client base URL: `/api/v1` instead of `/v1`.
- Integration tests + fixtures.
- Vite dev proxy in `frontend/vite.config.ts`: proxy `/api/v1`, `/api/auth`, plus health endpoints `/api/v1/healthz` / `/api/v1/readyz`.

### 3.12 Auth Lambda BFF decision

**Status**: Decided

**Lineage:** TypeScript on Node 22 — modern, well-typed Cognito SDK, fast cold starts, esbuild produces tiny zips. Lambda is the right shape because auth flow is bursty and HTTPOnly cookies require server-side Set-Cookie headers (cannot be done in browser JS).

**Chose:** Five TypeScript Lambdas on Node 22, packaged together via esbuild, deployed individually via Terraform.

**Function inventory**

| Function | Trigger | Purpose |
| --- | --- | --- |
| `login` | Function URL `/api/auth/login` | Builds Cognito hosted-UI URL with state + PKCE, returns 302 redirect. |
| `callback` | Function URL `/api/auth/callback` | Exchanges OAuth code for tokens, sets HTTPOnly cookies, defensive UPSERT into `users`, redirects to `/app`. |
| `refresh` | Function URL `/api/auth/refresh` | Uses `refresh_token` cookie to mint a new `access_token`; rotates the cookie. |
| `logout` | Function URL `/api/auth/logout` | Clears both cookies (Max-Age=0), revokes refresh token, redirects to `/`. |
| `post-confirmation` | Cognito User Pool trigger | Fires once when Cognito confirms a new identity. `INSERT INTO users (cognito_sub, email)`. |

**Stack**
- Runtime: Node 22 (LTS).
- Router: Hono (for the multi-endpoint functions).
- Bundler: esbuild → single zip per function or a shared layer.
- Secrets: SSM Parameter Store, fetched on cold start, cached in module scope.
- Cookies: `HttpOnly; Secure; SameSite=Lax; Path=/`. Access-token TTL 1h, refresh-token TTL up to 30 days.

### 3.13 User identity decision (Cognito ↔ Postgres)

**Status**: Decided

**Lineage:** Cognito `sub` is stable across logout/login cycles → use a Postgres `users.cognito_sub UNIQUE` column as the link. Row created by AWS-canonical Post-Confirmation Lambda Trigger, with defensive UPSERT in the BFF callback for resilience.

**Chose:** AWS-canonical sync pattern with belt-and-braces fallback.

**Schema**
```sql
CREATE TABLE users (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cognito_sub  TEXT NOT NULL UNIQUE,
  email        TEXT NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT now(),
  updated_at   TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE conversations ADD COLUMN user_id UUID REFERENCES users(id);
```

**Linkage**

Cognito assigns each identity a stable `sub` UUID. It does not change across logout / login / device. `users.cognito_sub UNIQUE` enforces a 1:1 mapping. Same Google account → same Cognito sub → same Postgres row.

**Row creation: Post-Confirmation Lambda Trigger (primary) + BFF UPSERT (defensive)**
- **Primary path**: the `post-confirmation` Lambda fires once when Cognito confirms a new user after Google federation. Runs `INSERT INTO users (cognito_sub, email) VALUES ($1, $2) RETURNING id`. Clean semantic boundary — signup = row creation; login = row read.
- **Defensive fallback**: the BFF `callback` Lambda always runs `INSERT INTO users (cognito_sub, email) VALUES ($1, $2) ON CONFLICT (cognito_sub) DO NOTHING`. If the trigger ever failed (transient DB blip, Aurora cold-start timeout), the user is never locked out.

**Per-request validation (FastAPI `SessionPort`)**
1. FastAPI middleware reads the `access_token` cookie from the request.
2. Validates the JWT signature against the Cognito JWKS (`https://cognito-idp.<region>.amazonaws.com/<pool>/.well-known/jwks.json`), cached in memory.
3. Verifies expiry, issuer, audience.
4. Extracts the `sub` claim.
5. Looks up `users.id` via `cognito_sub` (request-scoped memo + in-process LRU of 10K entries × 5 min TTL).
6. Attaches `current_user_id` to request context.
7. All `/api/v1/*` queries scope by `WHERE conversations.user_id = $current_user_id`.

**Rejected alternatives**
- **Pushing `users.id` back into Cognito as a `custom:` attribute**: requires Cognito Advanced Security tier ($0.05/MAU), creates a two-phase-commit failure mode, bloats the JWT, opens an attack surface (Cognito attrs are mutable from admin API), and still requires a DB fallback. No.
- **Pre-Token-Generation Lambda trigger**: paid tier, Lambda invocation on every token refresh, only valuable if you offload authorization at ALB/API-Gateway (we don't) or need offline JWT validation (we don't).

> **Multi-IdP gotcha (future):** If email/password sign-in is ever added alongside Google, account-linking risk appears (same email → two Cognito sub values). Mitigation: a Pre-Sign-Up Lambda Trigger calling `AdminLinkProviderForUser`. Out of scope today.

### 3.14 Postgres TTL decision

**Status**: Decided

**Lineage:** Aurora supports `pg_cron` natively → one-line cron statements purge expired rate-limit / cache rows. No external Lambda, no EventBridge, no extra IAM.

**Chose:** `pg_cron` extension on Aurora Postgres with daily DELETE jobs.

```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
  'rate-limit-sweep',
  '0 3 * * *',
  $$DELETE FROM rate_limit WHERE expires_at < now()$$
);

SELECT cron.schedule(
  'output-cache-sweep',
  '0 4 * * *',
  $$DELETE FROM output_cache WHERE expires_at < now()$$
);
```

Read-side queries also filter by `WHERE expires_at > now()` so the table is never the source of stale data even if the sweep is skipped.

### 3.15 Terraform stack split decision

**Status**: Decided

**Lineage:** One stack (mirror dev-infra's single-stack pattern) split into modules whose boundaries map to tear-down lifecycle classes. Module-level `terraform destroy -target=module.X` is the "go on holiday" lever; full `terraform destroy` kills the project.

See [Tear-down ergonomics](#38-tear-down-ergonomics-decision) for the full module table.

**State backend**: same pattern as today — S3 in shared-services, key `convfinqa/environmental/<account>/terraform.tfstate`. Already provisioned by the bootstrap stack.

---

## 4. Runtime flows

> Sequence diagrams for each flow live in [`aws-architecture.html`](./aws-architecture.html#flows). Numbered text equivalents below.

Each flow includes a sequence diagram and a numbered text equivalent. Every interaction with HTTPOnly cookies, Aurora wake-up, and the BFF UPSERT fallback is shown explicitly.

### 4.1 Sign-up flow (first-time user)

1. User browses to `app.convfinqa.francescoalbanese.dev`. SPA loads from S3 via CloudFront.
2. User clicks "Login with Google". SPA navigates to `/api/auth/login`.
3. BFF builds the Cognito hosted-UI URL with `state` and `PKCE` code challenge, returns 302 redirect.
4. Cognito hosted UI redirects the browser to Google's OAuth screen.
5. User signs into Google; Google redirects back to Cognito's IdP response endpoint with an auth code.
6. Cognito creates a new user in the User Pool (with a fresh stable `sub`). Cognito fires the **Post-Confirmation Lambda Trigger**.
7. Post-Confirmation Lambda runs `INSERT INTO users (cognito_sub, email) VALUES (...) RETURNING id`. Row created.
8. Cognito redirects the browser to `/api/auth/callback?code=...&state=...`.
9. BFF callback exchanges the code for tokens (access, refresh, id) via Cognito's token endpoint.
10. BFF runs the **defensive UPSERT**: `INSERT INTO users (cognito_sub, email) ... ON CONFLICT (cognito_sub) DO NOTHING`. In the happy path, this no-ops (the trigger already created the row); if the trigger failed, this saves the user from being locked out.
11. BFF returns 302 to `/app` with two `Set-Cookie` headers: `access_token` (1h TTL) and `refresh_token` (30d TTL), both `HttpOnly; Secure; SameSite=Lax; Path=/`.
12. Browser stores cookies. Every subsequent request to `app.convfinqa.francescoalbanese.dev` automatically includes them.

### 4.2 Sign-in flow (returning user)

1. User clicks "Login with Google" (or is silently redirected because Google still has a session).
2. Cognito recognises the existing user by Google sub → returns the **same Cognito sub** as their first sign-up.
3. **Post-Confirmation trigger does NOT fire** — Cognito only fires it on first confirmation.
4. BFF exchanges code for tokens.
5. BFF runs the defensive UPSERT — no-op (row exists).
6. BFF sets fresh cookies and redirects to `/app`.

### 4.3 Streaming chat request flow

1. SPA posts a chat message to `/api/v1/chat/stream`. Browser attaches the `access_token` cookie automatically (same-origin).
2. CloudFront forwards the request (and the `Cookie` header, thanks to the `Managed-AllViewer` origin request policy) to the ALB.
3. ALB forwards to the Fargate task. FastAPI middleware (`SessionPort`) validates the JWT against Cognito JWKS (cached) and looks up `users.id`.
4. The use case acquires a Postgres advisory lock keyed on the conversation id to serialise concurrent requests for the same conversation.
5. FastAPI calls Bedrock via LiteLLM with prompt-cache markers. Bedrock streams text deltas.
6. Each delta is yielded as an SSE frame back through ALB → CloudFront → browser. CloudFront does not cache (CachingDisabled policy).
7. On stream finish, FastAPI persists the assistant message + token usage and emits the finish event.

### 4.4 Aurora cold-start scenario

1. User opens the app. SPA mounts and fires a fetch to `/api/v1/healthz` immediately.
2. SPA shows a "Waking up infrastructure..." loader.
3. FastAPI tries to query Aurora. Aurora is paused.
4. Aurora resumes — ~15 seconds (kept under 30s by the keep-alive Lambda pinging every ~20h).
5. Health check returns. SPA hides the loader.
6. By the time the user types and clicks Send, the connection pool is warm and the actual request is fast.

> **If the keep-alive Lambda has been broken for >24h** the first wake-up will be 30s+. Verify the keep-alive cron via CloudWatch metric `ServerlessDatabaseCapacity` being non-zero at ~20h intervals.

### 4.5 Tear-down / restore flow

1. **Running → Holiday**: trigger the `compute-destroy` GitHub Actions job (workflow_dispatch). Runs `terraform destroy -target=module.compute -target=module.keepalive`. ECS service, ALB, Lambda BFF zip, SSM params for the compute layer disappear. Aurora pauses naturally because no client is connected. Edge + DNS + data remain.
2. **Holiday → Running**: `git push` to trigger normal CI, or run `terraform apply` manually. ECS Express auto-wires ALB+task again. App is live in ~5 minutes.
3. **Anything → Dead**: full `terraform destroy`. Take an Aurora snapshot first if data matters. DNS records and ACM cert are removed; if you reapply later, the cert revalidation costs only the DNS-validation wait (~1-2 min).

### 4.6 CI/CD pipeline flow

**Why migrations gate backend-deploy**

Running `alembic upgrade head` as a one-shot Fargate task *before* the service update means a failed migration fails the workflow without rolling out the new image. The old image keeps running on the existing schema until you fix the migration. This is the safest sequencing for a single-task service that cannot orchestrate its own multi-step deploy.

---

## 5. Disqualified alternatives

Every alternative considered and the specific reason it was rejected. If you find yourself reconsidering one of these, read why it was killed first.

### Backend compute alternatives

| Option | Idle cost | Why rejected |
| --- | --- | --- |
| EKS | ~$72/mo control plane + nodes | $72/mo flat fee disqualifies for portfolio. K8s cost wins only kick in at 15+ continuously-running containers; we run 1-2. |
| App Runner | ~$5-7/mo floor | **Sunset.** AWS stopped accepting new App Runner customers on 2026-04-30. Official replacement: ECS Express Mode. |
| API Gateway HTTP API → ECS | — | HTTP API does not support response streaming. Hard dealbreaker for SSE. |
| API Gateway REST API → ECS | $3.50/M requests | Streams (Nov 2025 GA), but no built-in Cognito JWT authorizer (HTTP API has it, REST API doesn't). To get streaming + Cognito on the same endpoint you need REST API + custom Lambda authorizer — more moving parts than CloudFront → ALB direct. |
| Lambda Web Adapter + Function URL + SnapStart | ~$0 | Real option, AWS-published reference. User rejected on production-realism grounds for streaming AI agents. Kept on the table as a future cost optimisation if portfolio is ever literally untouched for months. |
| Fargate Spot baseline | ~70% discount | AWS guidance: Spot is not recommended for user-facing services (2-min reclamation warning). Used for autoscaling extras only. |
| Fargate, public subnet, no ALB, CloudFront → public task IP | ~$10-12/mo | Operationally fragile. CloudFront cannot round-robin across multiple origin IPs; Route53 multi-value answers don't fail over fast enough; task ENI rotates on replacement, leaving CloudFront pointing at a dead IP for minutes. |
| Fargate behind private ALB + CloudFront VPC Origins + NAT | ~$50+/mo | Higher security posture but ~$22-32/mo extra (NAT or VPC interface endpoints). The "private" benefit is invisible for a portfolio. |
| ECS Fargate hand-wired (without Express Mode) | ~$26-30/mo | Same cost as Express Mode but many hundred more lines of Terraform — auto-wiring is free LOC saving. |

### Database alternatives

| Option | Idle cost | Why rejected |
| --- | --- | --- |
| RDS Postgres db.t4g.micro always-on | $12-14/mo | Cheap but never zero. Aurora min 0 ACU is strictly better for "I want to bring infra down" with proper mitigations. |
| RDS Postgres db.t4g.micro with scheduled stop | ~$2/mo stopped | 1-2 min RDS restart on first traffic. Worse UX than Aurora's 15s resume; same scheduling complexity. |
| Aurora Serverless v2 min 0.5 ACU (always warm) | ~$43/mo | Three times more expensive than full ECS+ALB. No. |
| Aurora Serverless v1 | — | Superseded. Not a 2026 option. |
| Neon serverless Postgres | $0 free tier | Off-AWS. Breaks the all-AWS narrative. 0.5 GB storage limit on free tier could bite if many ConvFinQA docs are loaded. |
| Supabase Postgres | $0 free tier | Same off-AWS issue as Neon. Pauses after 7d inactivity by default. |
| EC2 self-managed Postgres | ~$3/mo | No backups, no HA, no failover, no patching. Don't. |

### Cache / rate-limit alternatives

| Option | Idle cost | Why rejected |
| --- | --- | --- |
| ElastiCache Redis on t4g.micro | ~$11/mo always-on | Sub-ms latency is invisible against multi-second LLM calls. Cost not justified. |
| ElastiCache Serverless Redis | ~$70/mo floor | Way above portfolio budget. |
| DynamoDB on-demand | $0 within free tier | Adds a second service in docker-compose (DynamoDB Local or alternative). LocalStack archived its public repo on 2026-03-23 — alternatives exist (MiniStack, Floci, Moto) but they're added complexity. Single-DB Postgres simpler. |
| In-process LRU only | $0 | Per-task; lost on deploy; doesn't help rate-limit semantics (needs to be cross-task). |

### User identity alternatives

| Option | Why rejected |
| --- | --- |
| `custom:postgres_user_id` attribute in Cognito | Requires Cognito Advanced Security tier ($0.05/MAU). Two-phase-commit failure mode at signup. JWT bloat. Mutable from Cognito admin API → attack surface. Still requires DB lookup fallback — so why have it. |
| Pre-Token-Generation Lambda Trigger | Same Advanced Security paid tier. Lambda runs on every token refresh. Only worth it if you offload authorization at ALB/API-Gateway (we don't) or need offline JWT validation (we don't). |
| UPSERT-in-BFF-only (no Post-Confirmation trigger) | User-rejected. The AWS-canonical pattern is Post-Confirmation trigger; we use it as primary with BFF UPSERT as resilience fallback. |
| ALB built-in Cognito auth (drop the BFF Lambdas) | ALB session cookie is opaque — the app cannot read the underlying Cognito tokens. User explicitly wants the raw tokens in HTTPOnly cookies. Incompatible. |

### DNS pattern alternatives

| Option | Why rejected |
| --- | --- |
| Pattern X — dev-infra writes records, convfinqa exports values via `terraform_remote_state` | Two-step apply dance per release (convfinqa pending cert → dev-infra writes validation → convfinqa finalises). More coupling, more brittle. |
| New hosted zone in convfinqa account, NS delegation from parent | User preference was "keep only one zone, in dev-infra". Pattern Y satisfies that with single-apply ergonomics. |

### API URL alternatives

| Option | Why rejected |
| --- | --- |
| Keep `/v1/*` (no `/api/` prefix) | Same-domain SPA + API. A future SPA client-side route called `/v1/something` would collide with the backend. `/api/v1/*` is the standard 2026 pattern for SPA-colocated APIs. |
| Backend on a separate subdomain `api.convfinqa...` | Cross-subdomain cookies → SameSite=None required → CORS preflight. Adds complexity for zero functional gain. |

---

## 6. 2026 research findings

Facts gathered from AWS docs, AWS blog posts, and engineering write-ups during the decision process. Citation-ready; cite the source URL on demand.

| Finding | Date / source | Impact on this stack |
| --- | --- | --- |
| CloudFront VPC Origins GA | Nov 2024 | Considered for keeping ALB private. Did NOT remove ALB cost, only changed access posture. Skipped. |
| CloudFront VPC Origins WebSocket support GA | May 2026 | Not applicable; SSE is the streaming model. |
| CloudFront VPC Origins cross-account GA | Nov 2025 | Not used; convfinqa runs in its own account. |
| Aurora Serverless v2 min 0 ACU GA | Nov 2024 | **Chosen.** Verified resume timing: 15s short pause, 30s+ deep sleep after >24h idle. |
| ECS Express Mode launch | re:Invent 2025 | **Chosen as backend compute model.** Auto-wires Fargate + ALB + scaling + networking. |
| AWS App Runner closed to new customers | 2026-04-30 | Disqualified. AWS-recommended replacement is ECS Express Mode. |
| HTTP API does NOT support response streaming | verified Dec 2024 community + AWS docs | API Gateway HTTP API ruled out. |
| REST API response streaming GA | Nov 2025 | Streams, but no built-in Cognito authorizer → CloudFront → ALB direct is simpler. |
| SnapStart for Python GA | 2024 | Considered for Lambda compute path. Incompatible with container-image Lambdas (zip only, 250 MB unzipped) — works for our deps if we ever pivot. |
| Fargate Spot guidance: not for user-facing services | AWS docs | Used only for autoscaling extras, not the baseline task. |
| LocalStack public repo archived | 2026-03-23 | Reinforces choice to avoid DynamoDB in dev (since DynamoDB Local + LocalStack-style alternatives are now in flux). Postgres-for-everything wins on dev-loop simplicity. |
| Cognito + Postgres canonical sync pattern | AWS samples (Cognito2RDS), pg-cognition library | Post-Confirmation trigger is the canonical pattern. We use it as primary with BFF UPSERT as fallback. |
| Pre-Token-Generation requires Cognito Advanced Security tier | AWS docs | $0.05/MAU after free tier. Justifies our rejection. |
| HTTPOnly cookies for token storage | AWS security guidance 2026 | "Apps should store tokens securely using httpOnly cookies or secure storage." Direct alignment with the chosen pattern. |

---

## 7. Operational runbook

Verification checks once the stack is applied, plus the three lifecycle levers.

### End-to-end verification checks

1. `dig app.convfinqa.francescoalbanese.dev +short` returns CloudFront IPs.
2. `curl -I https://app.convfinqa.francescoalbanese.dev/` returns 200 with HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy.
3. Visiting the URL in a browser loads the SPA bundle.
4. `curl -i https://app.convfinqa.francescoalbanese.dev/api/v1/healthz` returns 200.
5. A streamed chat round-trip works: open the app, send a message, observe `text/event-stream` frames in browser DevTools Network tab, response renders incrementally.
6. Aurora cold-start: leave the app idle 25h, click Send, verify the SPA "waking up" loader appears and the response completes within 30s.
7. Keep-alive working: CloudWatch metric `ServerlessDatabaseCapacity` shows non-zero values at ~20h intervals.
8. Cost target hit: under **$5/mo idle** when compute module is destroyed; under **$35/mo idle** when compute is up. Verify in AWS Cost Explorer after the first full month.

### Lifecycle levers

| Goal | Command | Result |
| --- | --- | --- |
| Stand up the stack | `terraform apply` (or merge to main triggers CI) | All modules applied. Live in ~5 minutes. |
| Going on holiday | Trigger `compute-destroy` workflow (workflow_dispatch) | ECS+ALB+Lambda BFF removed. Static site still loads. Aurora pauses naturally. Cost ≈ $1-2/mo. |
| Coming back | `terraform apply` | Compute layer re-created. ECS Express auto-wires ALB+task. Live in ~5 min. |
| Project dead | `terraform destroy` (full) | Everything gone. Take an Aurora snapshot first if data matters. |

### Unresolved questions (carry-overs from the design phase)

1. **Cognito User Pool location** — convfinqa account or shared-services? Recommended: convfinqa account (project-specific). $0 idle either way.
2. **Bedrock cross-region inference profile** — current model is `bedrock/eu.anthropic.claude-haiku-4-5-...`. Verify the convfinqa AWS account is enrolled in the EU inference profile and the ECS task role's IAM policy scopes the right region.
3. **Cognito Google IdP setup** — requires a Google Cloud OAuth client ID/secret. One-time manual step, not Terraform-able cleanly. Document in the deploy README.
4. **Documents seeder strategy** — if `module.data` is ever destroyed, alembic re-runs but seeded ConvFinQA documents are lost. Recommend the seeder runs as a one-shot CI step (`aws ecs run-task`) after data module recreation, NOT on every ECS task startup.
5. **Log strategy** — pick ALB access logs (recommended) over CloudFront response logs, or accept both for diagnostic value.

---

## 8. Glossary & critical files

### Glossary

| Term | Meaning |
| --- | --- |
| **ACU** | Aurora Capacity Unit. The compute unit for Aurora Serverless v2. 0 ACU means paused. 0.5 ACU ≈ 1 GiB RAM + corresponding CPU. |
| **ALB** | Application Load Balancer. L7 load balancer used as the ingress for the ECS service. Auto-wired by ECS Express Mode. |
| **BFF** | Backend for Frontend. A small backend (here, our Lambda functions) that exists specifically to serve the frontend — handles auth state, cookies, redirects, and shields the SPA from talking directly to Cognito. |
| **ECS Express Mode** | ECS deployment mode (re:Invent 2025) that auto-wires Fargate + ALB + cert + scaling + networking with sensible defaults. |
| **JWKS** | JSON Web Key Set. The public key set published by Cognito at `/.well-known/jwks.json` that lets you validate JWT signatures offline. |
| **OAC** | Origin Access Control. The modern way (2022+) for CloudFront to access a private S3 bucket. Replaces OAI. |
| **OIDC** | OpenID Connect. (1) The protocol Cognito uses for the Google federation; (2) the trust mechanism GitHub Actions uses to assume the AWS deploy role without long-lived keys. |
| **pg_cron** | Postgres extension that schedules SQL as cron jobs inside the database itself. Aurora supports it natively. We use it for nightly TTL sweeps on cache/rate-limit tables. |
| **PKCE** | Proof Key for Code Exchange. The OAuth code flow extension used by public clients (our SPA → Cognito) to prevent code interception. |
| **Post-Confirmation Lambda Trigger** | Cognito User Pool trigger that fires once when a user is confirmed (after Google federation completes). Used to create the matching `users` row in Postgres. |
| **SAN cert** | Subject Alternative Name certificate. A single ACM cert covering multiple DNS names (here: `app.convfinqa.francescoalbanese.dev` + `convfinqa.francescoalbanese.dev`). |
| **SnapStart** | Lambda feature that snapshots the JVM/Python init state for faster cold starts. GA for Python in 2024. |
| **SSE** | Server-Sent Events. The HTTP response streaming model used for chat tokens: `Content-Type: text/event-stream`, one frame per token. |
| **SSM Parameter Store** | AWS Systems Manager Parameter Store. KMS-encrypted key-value store; free tier sufficient for our secrets. |
| **VPC Origins (CloudFront)** | CloudFront feature (GA Nov 2024) that lets a CloudFront distribution use a private ALB/NLB/EC2 in a VPC as an origin. Not used here (we keep ALB public, locked to CloudFront prefix list). |

### Critical files referenced

| Path | What it is |
| --- | --- |
| `backend/src/convfinqa/adapters/persistence/sqlalchemy/engine.py` | Where the `create_async_engine` pool settings must be tuned (`pool_recycle=300`, etc.) for Aurora auto-pause to work. **Verified gap as of plan date.** |
| `backend/src/convfinqa/entrypoints/api/sse.py` | SSE streaming surface. Must remain compatible with ALB long-lived response forwarding (idle timeout, no buffering). |
| `backend/src/convfinqa/application/use_cases/send_message.py` | Per-conversation lock semantics. Implements the advisory-lock-based serialisation referenced in flow 4.3. |
| `backend/src/convfinqa/domain/ports/` | The hexagonal ports list. Adding `SessionPort`, `CachePort`, `RateLimitPort` means new files here. |
| `terraform/environmental/` | Existing bootstrap stack (OIDC + IAM only). The module split lives here. |
| `terraform/environmental/iam-github-actions.tf` | GitHub OIDC role + cross-account assume. New permissions added here as we discover them. |
| `frontend/vite.config.ts` | Dev-time proxy config. Must mirror prod path layout (`/api/v1`, `/api/auth`). |
| `../francescoalbanese-dev-infra/terraform/environmental/cloudfront.tf` | Reference SPA + CloudFront pattern. |
| `../francescoalbanese-dev-infra/terraform/environmental/main.tf` | How the parent zone is referenced as a data source via `aws.shared_services` provider — the pattern convfinqa mirrors. |

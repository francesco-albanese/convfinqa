# convfinqa AWS architecture — canonical reference

The stack is **ECS Express Mode** (Fargate-backed, auto-wired ALB) + **Aurora Serverless v2 min 0 ACU** + **S3/CloudFront SPA** + **TypeScript Lambda BFF** for Cognito-with-Google auth that sets HTTPOnly cookies. Cache, rate-limit, and idempotency live in the same Aurora cluster as Postgres tables. Secrets in SSM Parameter Store. One Terraform stack split into modules; `terraform destroy -target=module.compute` drops cost from ~$28/mo to ~$2/mo.

**Full architecture, rationale, runtime flows, disqualified alternatives, and decision lineage live in [`docs/aws-architecture.md`](../../../docs/aws-architecture.md). READ THAT FILE before touching `terraform/`, CloudFront behaviors, the Lambda BFF, the `users` schema, or anything that interacts with Cognito or Aurora. The companion [`docs/aws-architecture.html`](../../../docs/aws-architecture.html) holds only the rendered Mermaid diagrams (visual reference for humans).**

## Invariants that must not be violated without re-opening the design

- **Same-origin cookies**: auth (`/api/auth/*`) and API (`/api/v1/*`) MUST live on the same hostname as the SPA (`app.convfinqa.francescoalbanese.dev`). Do NOT split the backend onto `api.convfinqa.francescoalbanese.dev` — it breaks HTTPOnly cookie sharing and forces CORS.
- **No DynamoDB / Redis / ElastiCache** until measurements prove sub-ms cache latency is needed. Cache + rate-limit + idempotency stay in Postgres. New use cases must go through `CachePort` / `RateLimitPort` adapters so the future swap is one-file.
- **No NAT Gateway, no VPC interface endpoints for ECR/Logs/SSM**. The ECS task runs in a public subnet with `assignPublicIp: ENABLED` and a security group locked to the CloudFront origin-facing prefix list. This is the cost-floor invariant.
- **No RDS Proxy** — it pins connections and blocks Aurora auto-pause, defeating the whole reason we picked Aurora Serverless v2.
- **SQLAlchemy engine MUST set** `pool_recycle=300`, `pool_size=2`, `max_overflow=2`, `pool_pre_ping=True`. Current `backend/src/convfinqa/adapters/persistence/sqlalchemy/engine.py` only sets `pool_pre_ping=True` → Aurora will never pause until this is fixed.
- **User identity sync uses Post-Confirmation Lambda Trigger (primary) + defensive `INSERT ... ON CONFLICT (cognito_sub) DO NOTHING` in the BFF callback (fallback)**. Do NOT push `users.id` back into Cognito as a custom attribute — it requires the Advanced Security paid tier and creates a two-phase-commit failure mode.
- **TTL for `rate_limit` and `output_cache` uses `pg_cron`**, not an external Lambda or EventBridge cron. Aurora supports `pg_cron` natively.
- **Aggressive prompt caching against Bedrock** is a LiteLLM request-side feature (`cache_control` markers). Zero infrastructure required for it — never spin up Redis "for prompt caching".
- **API URL prefix is `/api/v1/*`** (NOT `/v1/*`) and auth is under `/api/auth/*`. This is non-negotiable for same-domain SPA + API.

## When in doubt

Open `docs/aws-architecture.md`. Search for the section that matches what you're about to change. The "Lineage" line on each decision is the punchline; the "Disqualified alternatives" section is where rejected options live with the specific reason. The matching diagrams are rendered in `docs/aws-architecture.html`.

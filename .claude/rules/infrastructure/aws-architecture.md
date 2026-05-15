---
name: aws-architecture
description: AWS stack invariants — ECS Express, Aurora min 0 ACU, same-origin cookies, no NAT, no DynamoDB/Redis
paths:
  - terraform/**
  - backend/src/convfinqa/adapters/persistence/**
  - backend/src/convfinqa/adapters/auth/**
last_validated: 2026-05-15
pillar: true
related:
  - convfinqa-aws-stack-design-may-2026-ecs-express
  - cognito-access-tokens-no-aud-claim-use-client
---

# convfinqa AWS architecture

Stack: **ECS Express Mode** (Fargate + auto-wired ALB) + **Aurora Serverless v2 min 0 ACU** + **S3/CloudFront SPA** + **TypeScript Lambda BFF** for Cognito-with-Google auth (HTTPOnly cookies). Cache, rate-limit, idempotency live in the same Aurora cluster. Secrets in SSM Parameter Store. One Terraform stack split into modules; `terraform destroy -target=module.compute` drops cost from ~$28/mo to ~$2/mo.

Full architecture, rationale, runtime flows, disqualified alternatives, decision lineage: [`docs/aws-architecture.html`](../../../docs/aws-architecture.html). **READ THAT FILE before touching `terraform/`, CloudFront behaviors, the Lambda BFF, the `users` schema, or anything that interacts with Cognito or Aurora.**

## Invariants (do not violate without re-opening the design)

- **Same-origin cookies**: auth (`/api/auth/*`) and API (`/api/v1/*`) MUST live on the same hostname as the SPA. Splitting backend to `api.<host>` breaks HTTPOnly cookie sharing and forces CORS.
- **No DynamoDB / Redis / ElastiCache** until measurements prove sub-ms cache latency is needed. Cache + rate-limit + idempotency stay in Postgres via `CachePort` / `RateLimitPort` adapters.
- **No NAT Gateway, no VPC interface endpoints for ECR/Logs/SSM**. ECS task runs in a public subnet with `assignPublicIp: ENABLED` + SG locked to the CloudFront origin-facing prefix list. This is the cost-floor invariant.
- **No RDS Proxy** — pins connections, blocks Aurora auto-pause, defeats picking Aurora Serverless v2.
- **SQLAlchemy engine MUST set** `pool_recycle=300`, `pool_size=2`, `max_overflow=2`, `pool_pre_ping=True`. Without these, Aurora never pauses.
- **User identity sync**: Post-Confirmation Lambda Trigger (primary) + defensive `INSERT ... ON CONFLICT (cognito_sub) DO NOTHING` in the BFF callback (fallback). Do NOT push `users.id` back into Cognito as a custom attribute — requires Advanced Security paid tier and creates two-phase-commit failure mode.
- **TTL for `rate_limit` and `output_cache` uses `pg_cron`**, not external Lambda/EventBridge cron. Aurora supports `pg_cron` natively.
- **Aggressive prompt caching against Bedrock** is a LiteLLM request-side feature (`cache_control` markers). Zero infra required — never spin up Redis "for prompt caching".
- **API URL prefix is `/api/v1/*`** (NOT `/v1/*`) and auth is `/api/auth/*`. Non-negotiable for same-domain SPA + API.

## When in doubt

Open `docs/aws-architecture.html`. The "Decision lineage" line on each decision is the punchline; "Disqualified alternatives" is where rejected options live with the reason.

---
description: Terraform stack map — module layout, AWS invariants, version pins
last_validated: 2026-05-15
related:
  - ../.claude/rules/infrastructure/aws-architecture.md
  - ../docs/aws-architecture.html
  - convfinqa-aws-stack-design-may-2026-ecs-express
  - aws-provider-v6-data-aws-region-current-name
  - bedrock-claude-haiku-4-5-from-london-eu
---

# `terraform/` — infrastructure

## Reading order

1. [`docs/aws-architecture.html`](../docs/aws-architecture.html) — full design with decision lineage and disqualified alternatives. Read first when touching anything.
2. [`.claude/rules/infrastructure/aws-architecture.md`](../.claude/rules/infrastructure/aws-architecture.md) — the invariants that must not be violated without re-opening the design.
3. This file — module layout and version pins.

## Module layout (`terraform/environmental/`)

| Module | Role |
|---|---|
| `network` | VPC, subnets, security groups, route tables |
| `data` | Aurora Serverless v2 cluster, SSM parameters |
| `edge` | CloudFront distribution, S3 SPA bucket, Cognito UserPool |
| `compute` | ECS Express service for FastAPI, ALB target group |
| `keepalive` | EventBridge cron + Aurora-ping Lambda (prevents auto-pause from cooling too long) |

`terraform destroy -target=module.compute` drops cost ~$28/mo → ~$2/mo.

## Version pins

- Terraform >= 1.14
- AWS provider >= 6.28.0
- AWS provider v6 deprecates `data.aws_region.current.name` — use `.id` instead.

## Tooling

- Use `tfenv` for version management.
- Run `tflint` before committing.
- After any terraform change, run `make fmt` to format recursively.

## Tags

Every resource carries:
- `franco:terraform_stack = <stack name>`
- `franco:environment = var.account_name`
- `franco:managed_by = "terraform"`

## Cross-account DNS

DNS records owned by this stack go into the parent `francescoalbanese.dev` zone in the shared-services account via the `aws.shared_services` provider alias.

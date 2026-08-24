# How to run the app

The application, PostgreSQL database, and development identity run locally in
Docker. Chat inference uses Amazon Bedrock through your existing AWS profile;
this workflow does not deploy AWS infrastructure. Bedrock requests can incur
normal model usage charges.

## Prerequisite

Configure a profile with access to the selected Bedrock model. For an SSO
profile, refresh it before starting:

```bash
aws sso login --profile sandbox-admin
```

Bedrock runs in `eu-west-2`. The Docker backend sets both `AWS_REGION` and
`AWS_DEFAULT_REGION` to `eu-west-2`.

## Start

```bash
AWS_PROFILE=sandbox-admin make up
```

This starts PostgreSQL on port 5432, FastAPI on port 8000, and Vite on port
5173. The backend applies migrations, seeds the dataset and local user, and
mounts `~/.aws` read-only for Bedrock credentials. Open
<http://localhost:5173>; local authentication is automatic.

## Verify

```bash
curl -s http://localhost:8000/healthz
curl -s http://localhost:5173/api/v1/me
```

Select a document in the UI and send a question to verify Bedrock streaming.

## Host development

Start PostgreSQL, migrate, and seed the local user:

```bash
docker compose up -d postgres
uv run alembic upgrade head
LOCAL_USER_ID=00000000-0000-4000-8000-000000000001 \
LOCAL_USER_EMAIL=local@convfinqa.test \
uv run python -m convfinqa.adapters.persistence.local_user_seeder
AWS_PROFILE=sandbox-admin AWS_REGION=eu-west-2 AWS_DEFAULT_REGION=eu-west-2 \
LANGFUSE_ENABLED=false make run
```

In another terminal:

```bash
cd frontend
VITE_LOCAL_USER_ID=00000000-0000-4000-8000-000000000001 \
VITE_LOCAL_USER_EMAIL=local@convfinqa.test \
pnpm dev
```

## Tests

```bash
make test
make frontend-test
make frontend-browser-integration
```

Tests use local PostgreSQL and deterministic test doubles; they do not call
Bedrock or deploy infrastructure.

## Stop

```bash
make down
```

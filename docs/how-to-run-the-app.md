# How to run the app

End-to-end walkthrough for booting the chat slice locally and verifying it works.

Two flows are supported:

- **Container flow** — `make up` builds and runs the app inside Docker alongside Postgres. Closest to production.
- **Host flow** — `make run` runs uvicorn on your host against compose's Postgres. Faster iteration with `--reload`.

Each step below shows the make target first; the underlying command sits in a "what this runs" callout in case Make is unavailable.

## 1. AWS credentials (Bedrock SSO)

The default `LLM_MODEL` is `bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0`, so the app needs AWS credentials with Bedrock invoke permissions. SSO into the sandbox account:

```bash
aws-login
switch-aws-env sandbox-admin
AWS_PROFILE=sandbox-admin aws sts get-caller-identity
```

The `get-caller-identity` call must return the sandbox account/role — if it errors, fix the AWS session before continuing.

### Container flow only — materialise STS credentials

```bash
make aws-creds
```

> **What this runs:** `aws configure export-credentials --profile $${AWS_PROFILE:-sandbox-admin} --format env-no-export > .aws.env`

Writes short-lived `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` into `.aws.env` (gitignored). Compose's `app` service loads this via `env_file`. Re-run when the SSO session expires (typically ~1 hour).

The host flow does not need this — `make run` reads credentials from your live `AWS_PROFILE`.

## 2. Environment file

```bash
cp .env.example .env
```

Edit the environment file with sandbox Cognito values before running the container flow: `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET`, `COGNITO_HOSTED_UI_BASE_URL`, `COGNITO_TOKEN_URL`, and `COGNITO_REVOKE_URL`. The auth and API containers fail fast when these are missing. Other defaults work against compose's Postgres on the host loopback.

## 3. Install Python dependencies

```bash
make sync
```

> **What this runs:** `uv sync`

## 4. Start the stack

### Container flow

```bash
make up
```

> **What this runs:** `docker compose up -d --build`

Builds the app image, starts Postgres, waits for its healthcheck, then starts `convfinqa-app`. The container's entrypoint runs `alembic upgrade head` before booting uvicorn on `0.0.0.0:8000`.

### Host flow

```bash
docker compose up -d postgres
uv run alembic upgrade head
make run
```

> **What `make run` runs:** `uv run main`

`docker compose ps` should show postgres as `healthy` before migrations run. `make run` keeps `Settings.api_host` at `127.0.0.1` (loopback) and supports `--reload` if `API_RELOAD=true`.

## 5. Verify

### Health

```bash
curl -s http://localhost:8000/healthz
# {"status":"ok"}
```

### Sync chat

```bash
curl -s http://localhost:8000/v1/chat \
  -H "X-User-Id: dev-user" \
  -H "content-type: application/json" \
  -d '{"message": "Say hello in five words."}'
```

Returns an Anthropic-shaped JSON envelope with `id`, `conversation_id`, `content`, `model`, `usage`, and `created_at`. Capture the `conversation_id` to continue the same thread on the next call.

### Streaming chat (Vercel AI SDK v5 UI Message Stream)

```bash
curl -N http://localhost:8000/v1/chat/stream \
  -H "X-User-Id: dev-user" \
  -H "accept: text/event-stream" \
  -H "content-type: application/json" \
  -d '{"message": "Stream me a haiku about ledgers."}'
```

`-N` disables curl's output buffering so SSE frames print as they arrive. The stream ends with `data: [DONE]`.

### CLI REPL

```bash
make cli ARGS="chat --user-id dev-user"
```

> **What this runs:** `AWS_PROFILE=sandbox-admin uv run convfinqa chat --user-id dev-user` (set `AWS_PROFILE` in your shell or `.env`).

Type a message and press enter. `/new` resets the conversation; `/exit` (or Ctrl-D) quits.

## 6. Stop the stack

```bash
make down
```

> **What this runs:** `docker compose down`

## Tests

```bash
make test
```

> **What this runs:** `make test-unit` then `make test-integration` (pytest with the `unit` / `integration` markers).

Tests spin up a Postgres testcontainer and run `alembic upgrade head` against it — no need to point them at the docker-compose database.

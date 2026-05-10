# How to run the app

End-to-end walkthrough for booting the chat slice locally and verifying it works.

## 1. AWS credentials (Bedrock)

The default `LLM_MODEL` is `bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0`, so the app needs AWS credentials with Bedrock invoke permissions.

```bash
aws-login
switch-aws-env sandbox-admin
AWS_PROFILE=sandbox-admin aws sts get-caller-identity
```

The `get-caller-identity` call must return the sandbox account/role — if it errors, fix the AWS session before continuing.

## 2. Environment file

```bash
cp .env.example .env
```

Edit `.env` if you want a different `LLM_MODEL`, `DATABASE_URL`, or `SYSTEM_PROMPT`. Defaults work against the Postgres container started in step 3.

## 3. Install Python dependencies

```bash
uv sync
```

## 4. Start Postgres

```bash
docker compose up -d postgres
```

Healthcheck is built in; the app can connect as soon as `docker compose ps` shows the container as `healthy`.

## 5. Apply migrations

```bash
uv run alembic upgrade head
```

This creates the `conversations` and `messages` tables against the URL in `DATABASE_URL`.

## 6. Boot the API

```bash
AWS_PROFILE=sandbox-admin uv run uvicorn convfinqa.main:create_app --factory --reload
```

The `--factory` flag is required — `create_app()` builds the FastAPI instance, it is not a module-level `app`.

## 7. Verify

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
AWS_PROFILE=sandbox-admin uv run convfinqa chat --user-id dev-user
```

Type a message and press enter. `/new` resets the conversation; `/exit` (or Ctrl-D) quits.

## Tests

```bash
uv run pytest -q tests/
```

Tests spin up a Postgres testcontainer and run `alembic upgrade head` against it — no need to point them at the docker-compose database.

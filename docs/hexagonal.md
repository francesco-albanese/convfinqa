# convfinqa — Hexagonal Architecture

> Worked example: `POST /chat/stream`. Visual diagrams (layered overview, sequence trace, container bootstrap, decision tree) live in [`hexagonal.html`](./hexagonal.html). This page is the textual reference.

## Where does code go?

Hexagonal architecture answers this with one question: **does this code know about the framework, the database, the LLM, or HTTP?** If yes, it goes on the outside. If no, it goes in the middle. The middle is the part you'd keep if you swapped FastAPI for Litestar and Postgres for SQLite.

There is a clear separation of domain, application, and infrastructure layers. ![diagram](./hexagonal-ddd.png)

---

## 1. The layers, at a glance

Dependencies point **inward**. Domain knows nothing. Application knows domain. Adapters know domain (and frameworks). Entrypoints know application + domain. The container is the only place that knows everyone.

| Layer | What lives here | Path | May import |
| --- | --- | --- | --- |
| **domain** | Business concepts. `Conversation`, `Message`, `StopReason`. **Ports** as `typing.Protocol`. | `backend/src/convfinqa/domain/` | stdlib only (`dataclasses`, `datetime`, `enum`, `typing`, `collections.abc`) |
| **application** | Use cases. Orchestrates domain + ports. `SendMessageUseCase.stream(...)`. | `backend/src/convfinqa/application/use_cases/` | `domain/` only |
| **adapters** | Port implementations. `LiteLLMAdapter`, `SqlAlchemyConversationRepository`. | `backend/src/convfinqa/adapters/` | `domain/` + frameworks (`sqlalchemy`, `litellm`, `boto3`, …). **NEVER** `application/` or `entrypoints/`. |
| **entrypoints** | HTTP routes, CLI, SSE framing, request/response models, error mapping. | `backend/src/convfinqa/entrypoints/` | `application/`, `domain/`, `container/`. **NEVER** `adapters/` directly. |
| **container** | Composition root. Instantiates adapters, wires them into use cases, attaches to `app.state`. | `backend/src/convfinqa/container.py` | everything (only file allowed to) |

The hexagon = pure code (domain + application). The "shell" = framework code (adapters + entrypoints). The container is what wires shell to hexagon, exactly once at startup.

---

## 2. Tracing a request: `POST /chat/stream`

A browser sends a JSON body. ~150ms later, an SSE stream begins. Every hop, and which layer owns it:

1. Browser → entrypoint: `POST /api/v1/chat/stream` with `ChatRequest` JSON. The entrypoint validates the body and resolves the `SendMessage` dependency from the container.
2. Entrypoint → use case: `send_message.stream(user_id, conversation_id, user_text, document_id)`. The use case resolves conversation + document via repository ports (domain entities returned).
3. Use case → lock adapter: `locks.try_acquire(conv_id)` returns an async context manager (`bool`). If `acquired = False`, yields `ConcurrentRequest` and exits.
4. Use case appends the user message via `conversations.append_message(...)`, yields `ConversationResolved` and `MessageStarted` events.
5. Use case builds the system prompt from the `Document` + framing, then streams chunks from the LLM port: `llm.stream(messages, system) → AsyncIterator[LLMChunk]`.
6. Loop until done — each `LLMChunk(text="...")` becomes a `TextDelta(text)` event the use case yields. The entrypoint translates each event to an SSE frame `data: {...}\n\n`.
7. On LLM finish: use case persists the assistant message via `conversations.append_message(assistant)` and yields `Finish(stop_reason, usage, created_at)`. Entrypoint writes the final SSE frame and closes the stream.
8. `to_ui_message_stream` translates domain events → Vercel AI UI v1 frames.

★ At every arrow above, the use case talks only to **ports** (Python `Protocol`s in `domain/ports/`). The concrete adapter was wired by the **container** at startup. The use case never imports `litellm`, `sqlalchemy`, or `fastapi`.

---

## 3. What lives in each layer (with real code)

### `entrypoints/` — the HTTP shell

Pydantic request/response models, FastAPI handlers, dependency injection, SSE framing, error → HTTP mapping. **Nothing else.** Routes don't decide business rules; they translate JSON in, translate events out.

```python
# backend/src/convfinqa/entrypoints/api/chat.py
async def stream_chat(
    body: ChatRequest,
    user_id: CurrentUserId,
    send_message: SendMessage,            # DI: SendMessageUseCase
) -> StreamingResponse:
    events = send_message.stream(
        user_id=user_id,
        conversation_id=body.conversation_id,
        user_text=body.message,
        document_id=body.document_id,
    )
    first_event = await anext(events)
    if isinstance(first_event, ConcurrentRequest):
        await events.aclose()
        raise ConversationBusyError(first_event.conversation_id)

    return StreamingResponse(
        to_ui_message_stream(prepend_event(first_event, events)),
        media_type="text/event-stream",
        headers=UI_MESSAGE_STREAM_HEADERS,
    )
```

`SendMessage` is an `Annotated[SendMessageUseCase, Depends(get_send_message)]` alias in `entrypoints/api/dependencies.py`. `get_send_message` reads the container off `request.app.state` — that's how the wired-up use case reaches the route.

### `application/` — the use case

A use case orchestrates a single business workflow. It depends on **domain entities** and **domain ports**. Never on a framework. The `SendMessageUseCase` takes four ports + a config string in its constructor; that's all it knows about the outside world.

```python
# backend/src/convfinqa/application/use_cases/send_message.py
class SendMessageUseCase:
    def __init__(
        self,
        llm: LLMPort,                          # Protocol from domain/ports
        conversations: ConversationRepository, # Protocol
        documents: DocumentRepository,         # Protocol
        locks: ConversationLockPort,           # Protocol
        system_prompt_framing: str,
    ) -> None:
        self._llm = llm
        self._conversations = conversations
        self._documents = documents
        self._locks = locks
        self._framing = system_prompt_framing

    async def stream(
        self, user_id: str, conversation_id: str | None,
        user_text: str, document_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent]:
        conversation, document = await self._resolve_conversation_and_document(...)
        system_prompt = build_system_prompt(self._framing, document)
        async with self._locks.try_acquire(conversation.id) as acquired:
            if not acquired:
                yield ConcurrentRequest(conversation_id=conversation.id)
                return
            # append user msg, stream LLM, persist assistant, yield events
```

Why one async-generator method? Because `/chat` (sync) and `/chat/stream` (SSE) **share this exact stream**. The sync handler aggregates events into a snapshot; the streaming handler forwards them as SSE frames. Two presenters, one truth — that's the hexagonal payoff.

### `domain/` — the heart

Entities (`Conversation`, `Message`, `Document`), value objects (`StopReason`, `Usage`, `Role`), and **ports as `typing.Protocol`**. Allowed imports: `dataclasses`, `datetime`, `enum`, `typing`, `collections.abc`. That's it.

```python
# backend/src/convfinqa/domain/ports/llm.py
class LLMPort(Protocol):
    def stream(
        self,
        messages: Sequence[LLMMessage],
        system: str,
    ) -> AsyncIterator[LLMChunk]: ...

# backend/src/convfinqa/domain/ports/repository.py
class ConversationRepository(Protocol):
    async def get(self, conversation_id: str, user_id: str) -> Conversation | None: ...
    async def create(self, user_id: str, document_id: str) -> Conversation: ...
    async def append_message(self, conversation_id: str, message: Message) -> None: ...
    async def list_for_user(self, user_id: str) -> tuple[ConversationSummary, ...]: ...
    async def get_messages(self, conversation_id: str, user_id: str) -> tuple[Message, ...] | None: ...

class DocumentRepository(Protocol):
    async def get(self, document_id: str) -> Document | None: ...

# backend/src/convfinqa/domain/ports/lock.py
class ConversationLockPort(Protocol):
    def try_acquire(self, conversation_id: str) -> AbstractAsyncContextManager[bool]: ...
```

Ports describe *what* the use case needs ("I need to stream chunks given some messages") without naming a vendor. Adapters supply the *how*.

### `adapters/` — the plug

One concrete class per port. Allowed to import frameworks (`litellm`, `sqlalchemy`, `boto3`). Forbidden from importing `application/` or `entrypoints/`.

| Port | Adapter | Role | Lives in |
| --- | --- | --- | --- |
| `LLMPort` | `LiteLLMAdapter` | litellm streaming | `adapters/llm/litellm_adapter.py` |
| `ConversationRepository` | `SqlAlchemyConversationRepository` | ORM get/create/append | `adapters/persistence/sqlalchemy/repository.py` |
| `DocumentRepository` | `SqlAlchemyDocumentRepository` | document fetch | `adapters/persistence/sqlalchemy/repository.py` |
| `ConversationLockPort` | `SqlAlchemyConversationLock` | PG advisory lock | `adapters/persistence/sqlalchemy/lock.py` |

Swap any one of these and the use case doesn't know. Tests construct a fake (e.g. `InMemoryConversationRepository`) and inject it via `Container.for_testing(...)`.

---

## 4. Bootstrap: how the container assembles the app

All wiring happens once, at FastAPI lifespan startup. After that, routes pull a ready-made `SendMessageUseCase` from `app.state.container`. No new adapters are constructed per request.

Composition order: `Settings` → infra clients (engine, session factory, LiteLLM client) → adapters → use case → `app.state`. After bootstrap, no code ever `new`s an adapter again.

```python
# backend/src/convfinqa/main.py
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = Container.bootstrap_application(settings=SETTINGS)
    app.state.container = container
    try:
        yield
    finally:
        await container.engine.dispose()

# backend/src/convfinqa/container.py — abbreviated
class Container:
    @classmethod
    def bootstrap_application(cls, settings: Settings) -> "Container":
        engine = create_async_engine(settings.database_url, ...)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        llm = LiteLLMAdapter(model=settings.llm_model, ...)
        conversations = SqlAlchemyConversationRepository(session_factory)
        documents = SqlAlchemyDocumentRepository(session_factory)
        locks = SqlAlchemyConversationLock(session_factory)

        send_message = SendMessageUseCase(
            llm=llm,
            conversations=conversations,
            documents=documents,
            locks=locks,
            system_prompt_framing=settings.system_prompt,
        )
        return cls(settings=settings, engine=engine, send_message=send_message, ...)
```

Tests call `Container.for_testing(settings=…, conversations=Fake…, llm=Fake…)` — same shape, fakes instead of real adapters.

---

## 5. "Where does this go?" — a 10-second decision tree

Walk the questions top-to-bottom; the first "yes" tells you where the file lands.

1. Is it an HTTP route / CLI command / SSE framing? (request validation, response shapes, error mapping) → **`entrypoints/`** (`api/`, `cli/`)
2. Does it orchestrate a workflow / use case? (multi-step, calls ports, yields events) → **`application/use_cases/`** (one async-gen method, shared by sync + stream presenters)
3. Does it talk to DB / LLM / external API? (`import sqlalchemy` / `litellm` / `boto3` / `httpx`?) → **`adapters/`** (implement a Protocol port)
4. Is it an entity, value object, or port? (data shape or contract — no I/O) → **`domain/`** (`entities`, `value_objects`, `ports/`)
5. Otherwise → it's wiring → **`container.py`**

### Do

- Define a port as `typing.Protocol` in `domain/ports/`.
- Inject ports into use case constructors. The use case never imports a concrete adapter.
- Instantiate every adapter inside `Container.bootstrap_application()`.
- Share one async-gen use case method between sync + streaming routes.
- For tests: build a fake in `tests/fakes/` implementing the same Protocol, inject via `Container.for_testing(...)`.

### Don't

- Import `fastapi`, `sqlalchemy`, `litellm` from `domain/` or `application/`.
- Import `application/` or `entrypoints/` from `adapters/`.
- Import `adapters/` from `entrypoints/`. Routes resolve adapters via container, not directly.
- Read `config.SETTINGS` in a route or adapter. Receive `Settings` from the container.
- Add a parallel `complete()` method beside the streaming use case — that's the drift hexagonal exists to prevent.

---

## 6. The audit greps (CI-enforced)

Any of these printing `VIOLATION` blocks merge:

```bash
grep -rE 'fastapi|sqlalchemy|litellm|pydantic_settings|pythonjsonlogger' backend/src/convfinqa/domain/ && echo VIOLATION
grep -rE 'fastapi|sqlalchemy|litellm' backend/src/convfinqa/application/ && echo VIOLATION
grep -rE 'convfinqa\.application|convfinqa\.entrypoints' backend/src/convfinqa/adapters/ && echo VIOLATION
grep -rE 'convfinqa\.adapters' backend/src/convfinqa/entrypoints/ && echo VIOLATION
```

---

## 7. Adding a new endpoint — recipe

Say you want `POST /conversations/{id}/regenerate`:

1. **Domain** — if you need a new port (e.g. `TokenCounterPort`), add a Protocol to `domain/ports/`. New event types (`Regenerated`) live next to existing dataclasses.
2. **Application** — write `RegenerateMessageUseCase` in `application/use_cases/regenerate_message.py`. Constructor takes ports. Expose one async-gen `stream(...)` method.
3. **Adapters** — implement any new port (e.g. `TiktokenCounter(TokenCounterPort)`) in `adapters/`. Existing repos/locks/LLM are reused.
4. **Container** — in `bootstrap_application`, instantiate the new adapter, build the use case, attach it on the container.
5. **Entrypoint** — add the FastAPI route in `entrypoints/api/`. Add a `Regenerate = Annotated[..., Depends(get_regenerate)]` alias in `dependencies.py`. The route only consumes events.
6. **Tests** — fakes for new ports in `tests/fakes/`; use case test asserts the event sequence; route test asserts SSE/HTTP behaviour through `Container.for_testing(...)`.

---

Canonical rule: [`.claude/rules/python/hexagonal.md`](../.claude/rules/python/hexagonal.md). Source diagram baseline: `POST /chat/stream` traced through commit `6c49390`.

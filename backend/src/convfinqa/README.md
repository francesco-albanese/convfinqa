---
description: Backend layer map (hexagonal) — where to look for what and which rules attach where
last_validated: 2026-05-15
related:
  - ../../../.claude/rules/python/hexagonal.md
  - ../../../.claude/rules/python/code-quality.md
  - ../../../docs/hexagonal.md
---

# `backend/src/convfinqa/` — layer map

Hexagonal architecture. Read [`hexagonal.md`](../../../.claude/rules/python/hexagonal.md) for the invariants (audit greps, settings DI, single-generator use case, timestamp single-source-of-truth).

```
entrypoints  →  application  →  domain
adapters     →  domain (via ports)
container.py →  composes adapters + use cases (the ONLY composition root)
```

| Dir | What lives here | Deep-dive |
|---|---|---|
| [`domain/`](domain/) | Frozen dataclasses, ports (`typing.Protocol`), pure domain logic. Zero framework imports. | [`domain/README.md`](domain/README.md) |
| [`application/`](application/) | Use cases, orchestration, streaming generators. Imports only `convfinqa.domain.*`. | [`application/README.md`](application/README.md) |
| [`adapters/`](adapters/) | Port implementations (sqlalchemy, litellm, cognito, etc.). Imports `domain` only. | [`adapters/README.md`](adapters/README.md) |
| [`entrypoints/`](entrypoints/) | FastAPI routes, Typer CLI. Depends on `application`, `domain`, `container`. | [`entrypoints/README.md`](entrypoints/README.md) |
| `container.py` | Wires adapters into use cases. `bootstrap_application()` (prod) + `for_testing()` (tests). | — |
| `config.py` | `Settings` model. `SETTINGS` is the lifespan bootstrap singleton — DO NOT read directly from routes/use cases/adapters; inject via `SettingsDep`. | — |
| `logging.py` | `get_logger(name)` — lazily configures JSON output. ALWAYS use this, never `logging.getLogger` directly. | [`../../../.claude/rules/python/logging.md`](../../../.claude/rules/python/logging.md) |

## Quick-check before merging

```bash
# These four must all be empty
grep -rE 'fastapi|sqlalchemy|litellm|pydantic_settings|pythonjsonlogger' domain/
grep -rE 'fastapi|sqlalchemy|litellm' application/
grep -rE 'convfinqa\.application|convfinqa\.entrypoints' adapters/
grep -rE 'convfinqa\.adapters' entrypoints/
```

If any prints output, you've drifted across a layer boundary.

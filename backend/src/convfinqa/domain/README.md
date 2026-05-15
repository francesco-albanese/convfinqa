---
description: Domain layer — pure model, frozen dataclasses, ports as Protocols. No framework imports.
last_validated: 2026-05-15
related:
  - ../README.md
  - ../../../../.claude/rules/python/hexagonal.md
---

# `domain/` — pure model

## Hard rule

Zero framework imports. Allowed: `dataclasses`, `datetime`, `enum`, `typing`, `collections.abc`. **Forbidden**: `fastapi`, `sqlalchemy`, `litellm`, `pydantic_settings`, `pythonjsonlogger`.

Pre-merge check:

```bash
grep -rE 'fastapi|sqlalchemy|litellm|pydantic_settings|pythonjsonlogger' . && echo VIOLATION
```

## Ports

Every port in `ports/` is a `typing.Protocol`, NOT an ABC. Methods are async where I/O is involved. Ports define the interface the application layer needs; adapters in `../adapters/` implement them.

## Value objects

Frozen dataclasses (`@dataclass(frozen=True)`). No Pydantic in domain — Pydantic belongs at the wire boundary in `entrypoints/`.

---
name: markdown-streaming
description: Streamdown (Vercel) is the ONLY markdown renderer for AI streaming chat surfaces. Never react-markdown
paths:
  - frontend/src/components/**
  - frontend/src/styles/**
last_validated: 2026-05-15
pillar: true
related:
  - frontend-markdown-renderer
---

# Markdown renderer — Streamdown ONLY

## Hard rule

**Use `streamdown` (Vercel) for assistant markdown. Never `react-markdown` + `remark-gfm`.**

Applies to every assistant-message renderer, every streaming-chat surface, every place LLM output reaches the DOM.

- `import { Streamdown } from "streamdown";` — never `import Markdown from "react-markdown"`
- GFM (tables, tasklists, autolinks, strikethrough, footnotes) is included by default. Do NOT add `remark-gfm` as a sibling — it's already inside Streamdown's `defaultRemarkPlugins`.
- The `components` prop is API-compatible with react-markdown — swap is a one-line change at the import.
- Required CSS wiring in `frontend/src/styles/globals.css`:
  ```css
  @import "streamdown/styles.css";
  @source "../../node_modules/streamdown/dist/*.js";
  ```
  The `@source` directive teaches Tailwind v4 to detect Streamdown's runtime classes.
- For plain text bubbles, pass `controls={false}`. Re-enable per feature when a ticket asks for table copy / code download / mermaid fullscreen.

## Why this rule

Streamdown handles incomplete markdown chunks (half-closed fences, unfinished tables, dangling `**`) during SSE without flicker. react-markdown + remark-gfm flicker. Streamdown is built by Vercel (same vendor as `@ai-sdk/react`, which we depend on) and powers the AI Elements `Response` component.

## Optional Streamdown plugins (lazy-add only)

- `@streamdown/code` — Shiki syntax highlighting
- `@streamdown/math` — KaTeX
- `@streamdown/mermaid` — Mermaid diagrams
- `@streamdown/cjk` — CJK text handling

Each adds bundle weight; don't install speculatively.

## Quick audit

```bash
# Must be empty
grep -rE "react-markdown|remark-gfm" frontend/src frontend/package.json
```

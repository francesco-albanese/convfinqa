# Markdown renderer for AI streaming chat — Streamdown ONLY

## Hard rule

**Use `streamdown` (Vercel) for rendering assistant markdown. Never `react-markdown` + `remark-gfm`.**

This applies to every assistant-message renderer, every streaming-chat surface, every place where LLM output reaches the DOM in this repo.

- `import { Streamdown } from "streamdown";` — never `import Markdown from "react-markdown"`
- GFM (tables, tasklists, autolinks, strikethrough, footnotes) is included out of the box. Do NOT add `remark-gfm` as a sibling — it's already inside Streamdown's `defaultRemarkPlugins`.
- The `components` prop is API-compatible with react-markdown (same shape: `{ p, ul, ol, li, strong, em, code, pre, a, ... }`), so swapping renderers is a one-line change at the import.
- Required CSS wiring in `frontend/src/styles/globals.css`:
  ```css
  @import "streamdown/styles.css";
  @source "../../node_modules/streamdown/dist/*.js";
  ```
  The `@source` directive teaches Tailwind v4 to detect the utility classes Streamdown emits at runtime. The path is relative to the CSS file.
- For the simple text-bubble case (no code-block copy buttons, no table controls), pass `controls={false}`. Re-enable per feature when a ticket asks for table copy / code download / mermaid fullscreen.

## Why this rule exists

The convfinqa-rb3.6 ticket originally specified `react-markdown` + `remark-gfm`. Both work, but they have a known failure mode in AI streaming chat: incomplete markdown chunks (half-closed fences, unfinished tables, dangling `**`) flicker or render as plain `**word` while the SSE stream is mid-flight. Streamdown was built by Vercel — same vendor as `@ai-sdk/react`, which we already depend on — specifically to fix this: it parses incomplete markdown, ships prompt-injection hardening, and powers the AI Elements `Response` component in the Vercel AI SDK. It is the canonical renderer for this stack.

`remark-gfm`'s irregular release cadence (v4.0.1 in Feb 2025, v4.0.0 in Sep 2024) is not abandonment — the project is mature and narrow — but consolidating on Streamdown removes one dependency, removes the manual `remarkPlugins={[remarkGfm]}` wiring, and matches the AI SDK ecosystem we already use.

## Optional Streamdown plugins (lazy-add only when a ticket asks)

- `@streamdown/code` — Shiki syntax highlighting
- `@streamdown/math` — KaTeX
- `@streamdown/mermaid` — Mermaid diagrams
- `@streamdown/cjk` — CJK text handling

Each adds bundle weight; do NOT install them speculatively. The base `streamdown` package is enough for `MessageBubble` and any other plain assistant-text renderer.

## Quick audit

```bash
# Must be empty
grep -rE "react-markdown|remark-gfm" frontend/src frontend/package.json
```

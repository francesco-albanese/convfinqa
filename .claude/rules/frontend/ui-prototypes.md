---
name: ui-prototypes
description: example-html/ contains the canonical visual mockups for every UI epic — port faithfully, don't load full HTML into context
paths:
  - frontend/src/components/**
  - frontend/src/routes/**
  - frontend/src/styles/**
last_validated: 2026-05-15
pillar: false
related:
  - example-html
---

# UI prototypes — `example-html/` is the design source of truth

## Hard rule

Every UI epic MUST consult the matching mockup in `example-html/` BEFORE writing components. These are Claude-Design HTML exports defining layout, spacing, typography, colour, motion, component anatomy. **Port faithfully, don't freelance.**

## File index

Desktop (≥1024px): `A` sign-in, `B` sign-up + Google OAuth, `C` empty `/app`, `D` doc pinned, `E` mid-stream + reasoning + citations, `F` light theme.
Mobile (<768px): `G` empty, `H` doc pinned + chat, `I` library bottom sheet, `J` history drawer, `K` light theme.
Tablet (768–1023px): `L` doc pinned, `M` light theme.

## Epic → mockup mapping

| Epic | Mockups |
|---|---|
| `gbl` empty app shell + sidebar | C, G, J |
| `ebw` sign-in + AuthProvider | A, B |
| `dj6` document picker | C→D, I |
| `9ye` pin doc + financial table | D, E, H, L |
| `uf5` light theme toggle | F, K, M |
| `bmu` stop button + stream error | E |
| `bqx` responsive sidebar + right-panel drawer | C+D, G+H+I+J, L+M |

## Workflow (CRITICAL)

The files are 2–11 MB self-contained HTML. **Do NOT load whole files into agent context** — they'll blow the budget.

1. `open "example-html/<file>.html"` for the visual reference.
2. `grep` for tokens when porting:
   ```bash
   grep -oE '--[a-z-]+:\s*[^;]+;' "example-html/D _ Document pinned _ ready for follow-up.html" | sort -u
   ```
3. Port to Tailwind v4 tokens in `frontend/src/styles/design-tokens.css`, components in `frontend/src/components/**` using shadcn + Streamdown. Never paste raw mockup HTML into the app.

## What "faithful" means

Match: layout & spacing, typography, colour & elevation tokens, motion (`--ease` curve + durations), component anatomy.

Don't copy: the mockup's hand-rolled DOM/CSS/JS, lorem-ipsum, magic numbers (go through tokens).

## When mockup and PRD disagree

Mockup wins on **visual surface**. PRD wins on **behaviour**. If conflict is structural (mockup shows a feature not in scope), stop and ask.

## Breakpoints

- Mobile: `<768px` (G–K)
- Tablet: `768–1023px` (L–M)
- Desktop: `≥1024px` (A–F)

`bqx` is the only ticket that touches all three; everything else implements desktop first.

# UI prototypes — `example-html/` is the canonical design reference

## Hard rule

**Every UI epic (`gbl`, `ebw`, `dj6`, `9ye`, `uf5`, `bmu`, `bqx`, and any future M2/M3/M4 frontend ticket) MUST consult the matching HTML mockup in `example-html/` BEFORE writing components.** These are high-fidelity prototypes generated with Claude Design — they define the layout, spacing, typography, colour palette, motion, and component anatomy the implementation must match.

Do not freelance the UI. Do not "iterate on the design" — port it faithfully.

## File index

Mockups live at the repo root in `example-html/` and are organised by viewport:

### Desktop (≥1024px)

| File | Surface |
|---|---|
| `A _ Sign in.html` | Sign-in page |
| `B _ Sign up _ Google OAuth handoff.html` | Sign-up page + Google OAuth handoff |
| `C _ Empty state _ no doc pinned.html` | `/app` with no chat and no document pinned |
| `D _ Document pinned _ ready for follow-up.html` | `/app` with a document pinned, ready to chat |
| `E _ Mid-stream _ reasoning trace _ cell-level citations.html` | Active streaming response with reasoning trace + cell-level citations |
| `F _ Light theme.html` | Light-theme variant of the doc-pinned surface |

### Mobile (<768px)

| File | Surface |
|---|---|
| `G _ Empty state.html` | Mobile empty `/app` |
| `H _ Doc pinned _ mid conversation.html` | Mobile doc-pinned + in-progress chat |
| `I _ Library bottom sheet.html` | Document picker as bottom sheet |
| `J _ History drawer.html` | Sidebar / chat history as left drawer |
| `K _ Mobile _ light theme.html` | Mobile light-theme variant |

### Tablet (768–1023px)

| File | Surface |
|---|---|
| `L _ Tablet _ doc pinned.html` | Tablet doc-pinned |
| `M _ Tablet _ light.html` | Tablet light-theme variant |

## Epic → mockup mapping

| Epic | Required mockups |
|---|---|
| `gbl` empty app shell + sidebar | C (desktop), G (mobile), J (sidebar drawer mobile) |
| `ebw` sign-in stub + AuthProvider seam | A, B |
| `dj6` document picker | C → D (desktop open/close), I (mobile bottom sheet) |
| `9ye` pin doc + render financial table | D, E (desktop), H (mobile), L (tablet) |
| `uf5` light theme toggle | F (desktop), K (mobile), M (tablet) — compare against dark variants D/E/H/L |
| `bmu` stop button + stream error UI | E (active stream surface anchors the stop button + error banner) |
| `bqx` responsive sidebar + right-panel drawer | C+D (desktop baseline), G+H+I+J (mobile), L+M (tablet) |

## How to use the mockups

The files are 2–11 MB self-contained HTML exports. Do NOT load them into the agent context as a whole — they will blow the budget. Workflow:

1. **Open in a browser** (`open "example-html/D _ Document pinned _ ready for follow-up.html"`) for the visual reference. This is the source of truth for layout decisions.
2. **`grep` the file for tokens** when porting styles, e.g.:
   ```bash
   grep -oE '--[a-z-]+:\s*[^;]+;' "example-html/D _ Document pinned _ ready for follow-up.html" | sort -u
   ```
   to extract CSS custom properties (radius scale, shadow scale, accent colours, easing).
3. **Port to the real stack** — Tailwind v4 tokens in `frontend/src/styles/design-tokens.css`, global rules in `frontend/src/styles/globals.css`, components in `frontend/src/components/**` using shadcn primitives and Streamdown for markdown. Never paste raw mockup HTML into the app.

## Known token primitives (extracted from `G _ Empty state.html` — verify per file)

- Type: `Inter` (sans), `JetBrains Mono` (mono).
- Radius scale: `--radius-xs:4 --radius-sm:6 --radius-md:10 --radius-lg:14 --radius-xl:20` (px).
- Shadow scale: `--shadow-sm/-md/-lg` (custom inset + drop layers).
- Easing: `cubic-bezier(.2,.7,.3,1)` — single project ease curve.
- Accent palette: `--ac-blue`, `--ac-green`, `--ac-orange`, `--ac-red` (+ `-soft` and `-border` variants).
- Dark theme is the default surface; light theme (F/K/M) re-tints the same tokens.

When porting tokens, mirror these names in `design-tokens.css` so the mockup ↔ implementation diff is grep-able.

## What "faithful" means

- **Layout & spacing**: match. Three-panel grid widths, sidebar rail width, top-bar height, message-bubble padding, right-panel column width.
- **Typography**: match family, size scale, line-height, letter-spacing.
- **Colour & elevation**: match the token values; do not invent new ones.
- **Motion**: match the `--ease` curve and the duration the mockup uses for the same affordance (drawer open, sheet rise, sidebar collapse).
- **Component anatomy**: same parts in the same positions (avatar placement, citation chip shape, code-fence chrome, table sticky-first-column behaviour).

What is NOT in scope to copy literally:
- The mockup's embedded HTML/CSS/JS. The implementation uses React, TanStack, shadcn, Streamdown, Tailwind v4 — never the mockup's hand-rolled DOM.
- Lorem-ipsum content. Replace with real or seeded fixtures.
- Magic numbers. Always go through the token layer.

## When mockup and PRD disagree

Mockup wins on **visual surface** (layout, spacing, type, colour, motion). PRD wins on **behaviour** (which endpoint, which event, which state machine, which test). If the conflict is structural (e.g. the mockup shows a feature not in scope this slice), stop and ask — do not silently extend scope.

## Responsive breakpoints

- Mobile: `<768px` — mockups G–K
- Tablet: `768–1023px` — mockups L–M
- Desktop: `≥1024px` — mockups A–F

`bqx` (responsive epic) is the only ticket that touches all three; everything else implements the desktop mockup first and lets `bqx` retrofit the breakpoints.

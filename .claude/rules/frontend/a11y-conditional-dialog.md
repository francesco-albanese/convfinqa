# Conditional role="dialog" + aria-modal on a non-button element

## The trap

When an existing element (typically `<aside>`) needs to behave as a modal dialog only under certain conditions (e.g., below a breakpoint, when an overlay store is open), the natural authoring pattern is:

```tsx
<aside
  role={isModal ? "dialog" : undefined}
  aria-modal={isModal ? true : undefined}
  aria-label={isModal ? "Sidebar drawer" : undefined}
>
```

Biome's `lint/a11y/useAriaPropsSupportedByRole` rule **false-positives** on this. The static analyser cannot prove that `aria-modal` is only set when `role="dialog"` is also set — it sees `aria-modal` on `<aside>` (implicit role `complementary`, which does not support `aria-modal`) and flags it.

## The fix — spread a typed attrs object

Build the modal attribute set as an object and spread it onto the JSX element. Biome cannot introspect spread keys, so the rule does not fire. The runtime behaviour is identical.

```tsx
const dialogProps: Record<string, unknown> = isModal
  ? {
      role: "dialog",
      "aria-modal": true,
      "aria-label": "Sidebar drawer",
      tabIndex: -1,
    }
  : {};

<aside ref={shellRef} data-testid="sidebar-shell" {...dialogProps} className={...}>
```

Canonical usages: `frontend/src/routes/_authed.tsx` (sidebar drawer), `frontend/src/components/RightPanel.tsx` (right-panel sheet).

## What NOT to do

- **Do not** `// biome-ignore lint/a11y/useAriaPropsSupportedByRole`. The rule is not wrong in general — `<aside aria-modal>` without `role="dialog"` is genuinely invalid. We want the rule to keep firing on accidental cases; the spread is a targeted opt-out only when the pairing is conditional.
- **Do not** force `role="dialog"` unconditionally to silence the lint. A non-modal `<aside>` should NOT be announced as a dialog by screen readers.
- **Do not** drop the implicit `<aside>` and switch to `<div role="dialog">`. The element should keep its semantic identity in the desktop layout; only the *modal-when-mobile* case needs the dialog role.

## Companion: focus trap + Escape

When you set `role="dialog"` + `aria-modal="true"` you also owe the user:
- focus trap (Tab/Shift+Tab cycles within the dialog)
- Escape-to-close
- initial focus on open
- return focus to the trigger on close

Use `useModalDialog` from `frontend/src/lib/ui/useModalDialog.ts` — it handles all four. Pair with `data-modal-initial-focus` on the element you want focused first inside the dialog, or accept the first-focusable fallback.

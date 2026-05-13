# CSV "Copy / Download" surfaces — neutralise formula prefixes

## The trap

When the frontend lets a user copy or download a CSV (think "Copy as CSV", "Export to spreadsheet"), Excel/Sheets/Numbers interpret any cell that **starts** with one of `=`, `+`, `-`, `@`, `\t`, `\r` as a **formula** on paste. RFC-4180 mechanical escaping (quoting `"`, `,`, `\r`, `\n`) does **NOT** defend against this — it's a separate threat class:

- `=HYPERLINK("http://evil","x")` → renders a clickable link
- `=cmd|'/c calc'!A0` → DDE → potential RCE (legacy Excel)
- `=WEBSERVICE(...)` → silent data exfil on cell focus
- `@SUM(A1:A9)` → formula evaluation

OWASP-style mitigation: prepend a literal `'` (single apostrophe) to any field starting with a dangerous prefix. Excel renders the value as text and the apostrophe disappears from the cell.

## The rule

For every CSV-emitting helper in the frontend:

1. **Sanitise string cells, row labels, and column headers.** Prepend `'` when the first character is in `=`, `+`, `-`, `@`, `\t`, `\r`.
2. **Do NOT sanitise numeric cells.** A `-2913` financial value MUST round-trip as a number, not as the text `'-2913` — otherwise `SUM()` formulas the user adds will break. The threat surface is text, not numbers (a `number` literal cannot carry a formula payload).
3. Sanitisation runs **before** RFC-4180 escaping. Order matters: `escapeCsvField(neutraliseFormulaPrefix(value))`.
4. Cover the rule with unit tests: at minimum one case per prefix (`=`, `+`, `-`, `@`, `\t`, `\r`) and an explicit "negative number stays a number" case.

Canonical implementation: `frontend/src/lib/transforms/rowMajorToCsv.ts`.

## Why not sanitise everything

A blanket apostrophe-prefix on every cell breaks the dominant use case for "Copy as CSV": pasting numeric data into a spreadsheet for further analysis. Financial tables are predominantly negative-or-positive numbers; prefixing them all would force users to manually `Find and Replace '` every paste. The narrow rule (strings only) covers the actual threat (string-typed labels/headers) without UX collateral.

## When to also apply this

- Any "Export to CSV" download button.
- Any clipboard-write of tabular data.
- Server-side CSV endpoints that feed a download (Python: same rule, same prefixes, same escape order).
- Plain-text "Copy as TSV" surfaces (same prefixes work in tab-separated formats).

NOT needed for: JSON exports (no formula evaluation), `application/x-ndjson` streams, copy-as-Markdown (Markdown doesn't have formula syntax).

## Quick audit

```bash
# Find every CSV writer in the frontend
grep -rE "writeText.*csv|\.csv['\"]|\\\\r\\\\n" frontend/src/lib/transforms frontend/src/components | grep -v __tests__
```

Each match must go through a function that neutralises formula prefixes on string fields.

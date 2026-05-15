---
name: csv-injection
description: CSV/TSV download + clipboard surfaces must neutralise formula prefixes on string cells
paths:
  - frontend/src/lib/transforms/**
  - frontend/src/components/**
last_validated: 2026-05-15
pillar: true
related:
  - frontend/src/lib/transforms
---

# CSV injection — formula-prefix neutralisation

## The trap

When the UI lets a user copy or download CSV, Excel/Sheets/Numbers interpret a cell **starting** with one of `=`, `+`, `-`, `@`, `\t`, `\r` as a formula on paste. RFC-4180 escaping does NOT defend against this — separate threat class.

- `=HYPERLINK("http://evil","x")` → clickable link
- `=cmd|'/c calc'!A0` → DDE → potential RCE (legacy Excel)
- `=WEBSERVICE(...)` → silent data exfil
- `@SUM(A1:A9)` → formula evaluation

## The rule

For every CSV-emitting helper:

1. Sanitise **string cells, row labels, and column headers**. Prepend `'` when the first character is one of `=`, `+`, `-`, `@`, `\t`, `\r`.
2. Do NOT sanitise **numeric cells**. A `-2913` financial value must round-trip as a number so user `SUM()` formulas work. The threat is text-typed, not numeric.
3. Sanitisation runs **before** RFC-4180 escaping: `escapeCsvField(neutraliseFormulaPrefix(value))`.
4. Cover with unit tests: one case per prefix + an explicit "negative number stays a number" case.

Canonical implementation: `frontend/src/lib/transforms/rowMajorToCsv.ts`.

## Where it applies

- "Export to CSV" download buttons
- Clipboard-write of tabular data
- Server-side CSV endpoints
- "Copy as TSV" surfaces (same prefixes work in tab-separated)

NOT needed for: JSON exports, NDJSON streams, copy-as-Markdown.

## Quick audit

```bash
grep -rE "writeText.*csv|\.csv['\"]|\\\\r\\\\n" frontend/src/lib/transforms frontend/src/components | grep -v __tests__
```

Each match must go through a function that neutralises formula prefixes on string fields.

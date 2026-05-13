# JS object iteration order — integer-like string keys are reordered

## The trap

In V8 / SpiderMonkey / JavaScriptCore, `Object.keys`, `for...in`, `Object.entries`, and `JSON.parse`-then-iterate **do NOT preserve insertion order for keys that look like 32-bit unsigned integers** (e.g. `"0"`, `"2007"`, `"2008"`). Those keys iterate FIRST in ascending numeric order, then non-integer string keys in insertion order, then symbols.

```js
const obj = JSON.parse('{"Year ended June 30, 2009":1,"2008":2,"2007":3}');
Object.keys(obj);
// → ["2007", "2008", "Year ended June 30, 2009"]   // not the wire order!
```

This is the ECMAScript spec (`OrdinaryOwnPropertyKeys`), not a quirk. Every engine does it.

## When it bites this codebase

`convfinqa` documents are financial tables keyed by year (`table_data: { "Year ended June 30, 2009": {…}, "2008": {…}, "2007": {…} }`). Backend stores and emits the original wire order — typically newest-first. JS reorders to ascending numeric, which is BACKWARDS for display.

Discovered in `convfinqa-9ye.1`. Tracking the proper fix in `convfinqa-tha` (backend should emit a `column_order: list[str]` alongside `table_data`).

## Rule

For any data the backend hands the frontend keyed by arbitrary strings where **insertion order matters**:

1. **Do NOT rely on `Object.keys` / `for...in` / `Object.entries` to preserve API order.** If any key is an integer-like string, you'll lose it.
2. **Demand an explicit `…_order: string[]` array** from the API (or, when authoring the endpoint, return one yourself).
3. When the API can't be changed, structure the wire payload as an **array of `{key, value}` entries**, not a dict.
4. Inside tests that exercise insertion-order preservation, use **non-integer-like keys** (`"alpha"`, `"FY 2008"`, `"q1"`) so the test isn't accidentally green for the wrong reason. If you must test the integer-key behaviour, write an explicit "this is the JS spec, not our bug" test that documents the reordering.

## What's safe vs not

| Scenario | Safe? |
| --- | --- |
| `Map<string, V>` (any keys) | ✅ — `Map` preserves insertion order regardless of key shape |
| `Object` with only non-integer-like string keys | ✅ — insertion order preserved |
| `Object` with any integer-like string key (`"0"`, `"42"`, `"2007"`) | ❌ — integer-like keys jump to the front, ascending |
| `Array<[string, V]>` entries from an API | ✅ — array order is array order |
| `JSON.stringify(obj)` then `JSON.parse` round-trip | ❌ — re-parsing applies the reorder rule again |

## Why `Map` isn't a free pass

`Map` solves the in-memory ordering problem but the wire is still JSON and JSON is still an object. The reorder happens at `JSON.parse`. A `Map` only helps if you can avoid `JSON.parse` (e.g. parse a `[[k, v], …]` array shape instead, then `new Map(entries)`).

## Quick audit

```bash
# Find places that iterate an API-shaped dict and rely on order
grep -rEn "Object\.keys\(.+\.table_data|Object\.entries\(.+\.table_data" frontend/src
```

The result must be empty OR every match must be paired with an explicit `…_order` array driving the iteration.

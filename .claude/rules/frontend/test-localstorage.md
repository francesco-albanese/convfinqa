# localStorage in vitest+jsdom under Node 25+

## The trap

Node 25 ships an *unflagged* built-in `globalThis.localStorage` that is a null-prototype object with **zero methods** unless you pass `--localstorage-file=...`. The first time anything reads it you get the warning:

```
Warning: `--localstorage-file` was provided without a valid path
```

Vitest's `populateGlobal` (see `vitest/dist/chunks/index.*.js`) copies jsdom window keys onto the test global, **but skips any key already present on `global` that isn't in its hard-coded `KEYS` list**. `localStorage` is in neither `LIVING_KEYS` nor `OTHER_KEYS`, so Node 25's broken stub wins. The result: `window.localStorage.setItem` may or may not exist depending on what vitest copied, but `window.localStorage.clear` / `getItem` / `removeItem` are `undefined`. Tests blow up with `TypeError: window.localStorage.clear is not a function`.

## The fix

Install an in-memory `Storage` shim in `src/test/setup.ts` and clear it in `afterEach`:

```ts
function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() { return store.size; },
    clear: () => store.clear(),
    getItem: (k) => (store.has(k) ? (store.get(k) as string) : null),
    setItem: (k, v) => { store.set(k, String(v)); },
    removeItem: (k) => { store.delete(k); },
    key: (i) => Array.from(store.keys())[i] ?? null,
  };
}

Object.defineProperty(window, "localStorage", { configurable: true, value: createMemoryStorage() });
Object.defineProperty(window, "sessionStorage", { configurable: true, value: createMemoryStorage() });
```

This is already wired in `src/test/setup.ts`. Do **not** remove it without also removing every test that touches `localStorage` / `sessionStorage`.

## What NOT to do

- Don't `vi.stubGlobal("localStorage", ...)` in every test — boilerplate, easy to forget.
- Don't add a `node --no-experimental-localstorage` flag — it doesn't exist; the API is unconditional in v25.
- Don't downgrade Node — `~/.tool-versions` / CI / repo Makefile are aligned on the current LTS line.
- Don't switch to `happy-dom` — the rest of the suite assumes jsdom (e.g. `@testing-library/react` quirks).

## Why this matters

Every UI store that persists to `localStorage` (`sidebarStore`, future `themeStore` from `uf5`, etc.) relies on this shim. New persistence stores get unit tests for free; new tests should use `createSidebarStore()`-style **factories** so the persistence-roundtrip test can instantiate twice in one test without `vi.resetModules()`.

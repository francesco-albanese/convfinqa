# Vitest fake timers around Radix UI + TanStack Query

## The trap

`vi.useFakeTimers()` mocks **everything** by default: `setTimeout`, `setInterval`, `requestAnimationFrame`, `requestIdleCallback`, `queueMicrotask`, `performance.now`. Radix UI primitives (Dialog, Slider, Popover, Tooltip, DropdownMenu, etc.) rely on rAF for focus traps, scroll locks, and animation orchestration. TanStack Query v5 schedules state commits with React 19's scheduler which also uses rAF / idle callbacks under the hood.

The result: a test that renders a Radix `Dialog` (or any Radix overlay) under `vi.useFakeTimers()` hangs and times out at the default 5s — the focus trap never finishes mounting, queries never commit, `waitFor` never resolves. Symptom is a uniform 5s timeout on every test in the file, no other error message.

## The fix

For tests that exercise a debounced input inside a Radix overlay (e.g. `DocPicker` search box), use **real timers + `waitFor`** with a generous timeout:

```ts
it("debounces the search input", async () => {
  const fetchMock = vi.fn().mockResolvedValue(jsonResponse(SAMPLE));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<DocPicker open onOpenChange={vi.fn()} onSelect={vi.fn()} />);

  // initial fetch fires on mount
  await waitFor(() => expect(fetchMock).toHaveBeenCalled());

  await user.type(screen.getByRole("searchbox"), "jkhy");
  // synchronously right after typing: debounce window still open, no q= yet
  expect(
    fetchMock.mock.calls.some(([u]) => String(u).includes("q=jkhy"))
  ).toBe(false);

  await waitFor(
    () => {
      expect(
        fetchMock.mock.calls.some(([u]) => String(u).includes("q=jkhy"))
      ).toBe(true);
    },
    { timeout: 1000 },
  );
});
```

The synchronous assertion right after `await user.type(...)` is the debounce check: `userEvent.type` takes ~50ms in real time, well under the 200ms debounce window, so the debounced fetch URL must NOT yet contain the typed query at that moment.

## If you really need fake timers

For surfaces that don't render a Radix overlay AND don't depend on react-query commits (e.g. testing a pure debounce hook in isolation), you can scope `useFakeTimers` to just the clock APIs and leave rAF alone:

```ts
vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
```

This keeps `requestAnimationFrame` / `requestIdleCallback` real, so React 19 + Radix can still tick.

## Don't

- Don't add hand-rolled `flushAsyncWork` helpers using `vi.advanceTimersByTimeAsync(0)` to coax a Radix-hosted component awake — the issue isn't pending microtasks, it's rAF being frozen.
- Don't paper over the timeout with `it(..., { timeout: 30_000 })` — the test will still hang because the rAF chain never resolves; you'll just wait longer for the failure.
- Don't reach for `vi.useFakeTimers({ shouldAdvanceTime: true })` as a shortcut — it advances fake time alongside wall clock but rAF stays mocked, which is the actual culprit.

## Why this rule exists

`convfinqa-dj6.6` (DocPicker) first shipped with `vi.useFakeTimers()` + `vi.advanceTimersByTimeAsync` to test the 200ms search debounce. Every test in the file hit the 5s vitest timeout because the Radix Dialog's focus trap never mounted (rAF was frozen) and the initial useDocumentList query never committed. Switching to real timers + `waitFor` fixed all three tests in the same file without changing the component under test. Memory: `frontend-vitest-fake-timers-radix-dialog`.

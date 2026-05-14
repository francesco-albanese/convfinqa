import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
	applyMode,
	createThemeStore,
	THEME_STORAGE_KEY,
} from "@/theme/themeStore";

type ChangeListener = (event: MediaQueryListEvent) => void;

type FakeMediaQueryList = {
	matches: boolean;
	media: string;
	addEventListener: (type: "change", listener: ChangeListener) => void;
	removeEventListener: (type: "change", listener: ChangeListener) => void;
	addListener: () => void;
	removeListener: () => void;
	dispatchEvent: () => boolean;
	onchange: null;
	emitChange: (matches: boolean) => void;
};

function installMatchMediaMock(initialMatches: boolean): FakeMediaQueryList {
	const listeners = new Set<ChangeListener>();
	const mql: FakeMediaQueryList = {
		matches: initialMatches,
		media: "(prefers-color-scheme: light)",
		addEventListener: (_type, listener) => {
			listeners.add(listener);
		},
		removeEventListener: (_type, listener) => {
			listeners.delete(listener);
		},
		addListener: () => {},
		removeListener: () => {},
		dispatchEvent: () => true,
		onchange: null,
		emitChange: (matches) => {
			mql.matches = matches;
			const event = { matches } as unknown as MediaQueryListEvent;
			for (const listener of listeners) listener(event);
		},
	};
	vi.stubGlobal(
		"matchMedia",
		vi.fn(() => mql as unknown as MediaQueryList),
	);
	return mql;
}

describe("themeStore", () => {
	beforeEach(() => {
		window.localStorage.clear();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it("applyMode('light') resolves effectiveTheme to light regardless of system preference", () => {
		installMatchMediaMock(false);
		const store = createThemeStore();

		applyMode(store, "light");

		expect(store.state.mode).toBe("light");
		expect(store.state.effectiveTheme).toBe("light");
	});

	it("applyMode('system') with system=light yields effectiveTheme=light", () => {
		installMatchMediaMock(true);
		const store = createThemeStore();
		applyMode(store, "dark");

		applyMode(store, "system");

		expect(store.state.mode).toBe("system");
		expect(store.state.effectiveTheme).toBe("light");
	});

	it("matchMedia change event updates effectiveTheme when in system mode", () => {
		const mql = installMatchMediaMock(false);
		const store = createThemeStore();
		expect(store.state.effectiveTheme).toBe("dark");

		mql.emitChange(true);

		expect(store.state.effectiveTheme).toBe("light");
	});

	it("matchMedia change event is ignored when an explicit mode is set", () => {
		const mql = installMatchMediaMock(false);
		const store = createThemeStore();
		applyMode(store, "dark");

		mql.emitChange(true);

		expect(store.state.mode).toBe("dark");
		expect(store.state.effectiveTheme).toBe("dark");
	});

	it("persists mode so a fresh store reads the previous selection", () => {
		installMatchMediaMock(false);
		const first = createThemeStore();
		applyMode(first, "light");

		const second = createThemeStore();

		expect(second.state.mode).toBe("light");
		expect(second.state.effectiveTheme).toBe("light");
	});

	it("ignores invalid persisted values and falls back to 'system'", () => {
		installMatchMediaMock(false);
		window.localStorage.setItem(THEME_STORAGE_KEY, "neon");

		const store = createThemeStore();

		expect(store.state.mode).toBe("system");
		expect(store.state.effectiveTheme).toBe("dark");
	});
});

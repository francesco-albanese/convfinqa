import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setMode } from "@/theme/themeStore";
import { useApplyEffectiveTheme } from "@/theme/useApplyEffectiveTheme";

function installMatchMediaMock(initialMatches: boolean): void {
	vi.stubGlobal(
		"matchMedia",
		vi.fn(() => ({
			matches: initialMatches,
			media: "(prefers-color-scheme: light)",
			addEventListener: () => {},
			removeEventListener: () => {},
			addListener: () => {},
			removeListener: () => {},
			dispatchEvent: () => true,
			onchange: null,
		})),
	);
}

describe("useApplyEffectiveTheme", () => {
	beforeEach(() => {
		window.localStorage.clear();
		installMatchMediaMock(false);
		document.documentElement.removeAttribute("data-theme");
	});

	afterEach(() => {
		vi.unstubAllGlobals();
		document.documentElement.removeAttribute("data-theme");
		setMode("system");
	});

	it("writes the current effective theme on mount", () => {
		setMode("light");

		renderHook(() => useApplyEffectiveTheme());

		expect(document.documentElement.dataset.theme).toBe("light");
	});

	it("updates the <html data-theme> when setMode is called at runtime", () => {
		setMode("light");
		renderHook(() => useApplyEffectiveTheme());
		expect(document.documentElement.dataset.theme).toBe("light");

		act(() => {
			setMode("dark");
		});

		expect(document.documentElement.dataset.theme).toBe("dark");
	});

	it("resolves 'system' mode against prefers-color-scheme", () => {
		installMatchMediaMock(true);
		setMode("system");

		renderHook(() => useApplyEffectiveTheme());

		expect(document.documentElement.dataset.theme).toBe("light");
	});
});

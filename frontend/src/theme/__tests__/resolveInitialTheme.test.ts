import { describe, expect, it } from "vitest";
import { isThemeMode, resolveInitialTheme } from "@/theme/resolveInitialTheme";

describe("resolveInitialTheme", () => {
	it("returns light when no persisted value and system prefers light", () => {
		expect(resolveInitialTheme(null, true)).toBe("light");
	});

	it("returns dark when no persisted value and system prefers dark", () => {
		expect(resolveInitialTheme(null, false)).toBe("dark");
	});

	it("returns light when persisted 'system' and system prefers light", () => {
		expect(resolveInitialTheme("system", true)).toBe("light");
	});

	it("returns dark when persisted 'system' and system prefers dark", () => {
		expect(resolveInitialTheme("system", false)).toBe("dark");
	});

	it("honours persisted 'light' even when system prefers dark", () => {
		expect(resolveInitialTheme("light", false)).toBe("light");
	});

	it("honours persisted 'dark' even when system prefers light", () => {
		expect(resolveInitialTheme("dark", true)).toBe("dark");
	});

	it("falls back to system pref when persisted value is corrupt", () => {
		expect(resolveInitialTheme("neon", true)).toBe("light");
		expect(resolveInitialTheme("neon", false)).toBe("dark");
	});

	it("falls back to system pref when persisted value is an empty string", () => {
		expect(resolveInitialTheme("", true)).toBe("light");
	});
});

describe("isThemeMode", () => {
	it("accepts the three valid modes", () => {
		expect(isThemeMode("system")).toBe(true);
		expect(isThemeMode("light")).toBe(true);
		expect(isThemeMode("dark")).toBe(true);
	});

	it("rejects null, undefined, empty string, and random strings", () => {
		expect(isThemeMode(null)).toBe(false);
		expect(isThemeMode(undefined)).toBe(false);
		expect(isThemeMode("")).toBe(false);
		expect(isThemeMode("auto")).toBe(false);
	});
});

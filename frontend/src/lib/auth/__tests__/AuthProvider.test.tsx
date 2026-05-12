import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
	AUTH_STORAGE_KEY,
	AuthProvider,
	useAuth,
} from "@/lib/auth/AuthProvider";

function renderUseAuth() {
	return renderHook(() => useAuth(), { wrapper: AuthProvider });
}

describe("AuthProvider / useAuth", () => {
	it("starts with userId=null when localStorage is empty", () => {
		const { result } = renderUseAuth();
		expect(result.current.userId).toBeNull();
	});

	it("signIn writes a dev-user-* id, persists it, and exposes it via the hook", () => {
		const { result } = renderUseAuth();

		act(() => {
			result.current.signIn();
		});

		const { userId } = result.current;
		expect(userId).not.toBeNull();
		expect(userId).toMatch(/^dev-user-/);
		expect(window.localStorage.getItem(AUTH_STORAGE_KEY)).toBe(userId);
	});

	it("signOut clears storage and exposes userId=null", () => {
		const { result } = renderUseAuth();

		act(() => {
			result.current.signIn();
		});
		expect(result.current.userId).not.toBeNull();

		act(() => {
			result.current.signOut();
		});

		expect(result.current.userId).toBeNull();
		expect(window.localStorage.getItem(AUTH_STORAGE_KEY)).toBeNull();
	});

	it("hydrates an existing dev-user-* id from storage on mount", () => {
		window.localStorage.setItem(AUTH_STORAGE_KEY, "dev-user-abc-123");
		const { result } = renderUseAuth();
		expect(result.current.userId).toBe("dev-user-abc-123");
	});

	it("ignores storage values that lack the dev-user- prefix", () => {
		window.localStorage.setItem(AUTH_STORAGE_KEY, "garbage-value");
		const { result } = renderUseAuth();
		expect(result.current.userId).toBeNull();
	});

	it("throws when useAuth is called outside an AuthProvider", () => {
		expect(() => renderHook(() => useAuth())).toThrow(
			/useAuth must be used within an <AuthProvider>/,
		);
	});
});

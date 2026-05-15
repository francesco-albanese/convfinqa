import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "@/lib/auth/AuthProvider";

function meOk(userId = "user-uuid-1", email = "user@test.com") {
	return new Response(JSON.stringify({ user_id: userId, email }), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

function meUnauthed() {
	return new Response(null, { status: 401 });
}

function renderUseAuth() {
	return renderHook(() => useAuth(), { wrapper: AuthProvider });
}

describe("AuthProvider / useAuth — session check", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("starts as loading then resolves to authed when /api/v1/me returns 200", async () => {
		vi.stubGlobal("fetch", vi.fn().mockResolvedValue(meOk()));
		const { result } = renderUseAuth();

		expect(result.current.status).toBe("loading");

		await waitFor(() => {
			expect(result.current.status).toBe("authed");
		});
		expect(result.current.userId).toBe("user-uuid-1");
		expect(result.current.email).toBe("user@test.com");
	});

	it("resolves to unauthed when /api/v1/me returns 401 and refresh also fails", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockResolvedValue(new Response(null, { status: 401 })),
		);
		const { result } = renderUseAuth();

		await waitFor(() => {
			expect(result.current.status).toBe("unauthed");
		});
		expect(result.current.userId).toBeNull();
		expect(result.current.email).toBeNull();
	});

	it("resolves to authed when /api/v1/me 401s but refresh succeeds and retry returns 200", async () => {
		let callCount = 0;
		vi.stubGlobal(
			"fetch",
			vi.fn().mockImplementation((input: RequestInfo | URL) => {
				const url = typeof input === "string" ? input : input.toString();
				if (url === "/api/auth/refresh") {
					return Promise.resolve(new Response(null, { status: 200 }));
				}
				callCount += 1;
				if (callCount === 1) {
					return Promise.resolve(meUnauthed());
				}
				return Promise.resolve(meOk());
			}),
		);
		const { result } = renderUseAuth();

		await waitFor(() => {
			expect(result.current.status).toBe("authed");
		});
	});

	it("resolves to unauthed when fetch throws", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockRejectedValue(new Error("network error")),
		);
		const { result } = renderUseAuth();

		await waitFor(() => {
			expect(result.current.status).toBe("unauthed");
		});
	});
});

describe("AuthProvider / useAuth — signIn", () => {
	it("navigates to /api/auth/login", () => {
		vi.stubGlobal("fetch", vi.fn().mockResolvedValue(meOk()));
		let capturedHref = "";
		vi.stubGlobal("location", {
			get href() {
				return capturedHref;
			},
			set href(v: string) {
				capturedHref = v;
			},
		});

		const { result } = renderUseAuth();

		act(() => {
			result.current.signIn();
		});

		expect(capturedHref).toBe("/api/auth/login");
	});
});

describe("AuthProvider / useAuth — signOut", () => {
	it("POSTs to /api/auth/logout and sets status to unauthed", async () => {
		const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url === "/api/v1/me") return Promise.resolve(meOk());
			return Promise.resolve(new Response(null, { status: 200 }));
		});
		vi.stubGlobal("fetch", fetchMock);

		const { result } = renderUseAuth();

		await waitFor(() => {
			expect(result.current.status).toBe("authed");
		});

		await act(async () => {
			await result.current.signOut();
		});

		expect(result.current.status).toBe("unauthed");
		expect(result.current.userId).toBeNull();
		const logoutCall = fetchMock.mock.calls.find(([u]) =>
			String(u).includes("/api/auth/logout"),
		);
		expect(logoutCall).toBeDefined();
		expect(logoutCall?.[1]).toMatchObject({ method: "POST" });
	});
});

describe("AuthProvider / useAuth — error boundary", () => {
	it("throws when useAuth is called outside an AuthProvider", () => {
		expect(() => renderHook(() => useAuth())).toThrow(
			/useAuth must be used within an <AuthProvider>/,
		);
	});
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import { routeTree } from "@/routeTree.gen";

const TEST_USER = { user_id: "guard-test-user", email: "guard@test.com" };

vi.mock("@/lib/chat/useConvfinqaChat", () => ({
	useConvfinqaChat: () => ({
		id: "stub",
		messages: [],
		status: "ready",
		setMessages: () => undefined,
		error: undefined,
		clearError: () => undefined,
		resumeStream: async () => undefined,
		regenerate: async () => undefined,
		addToolResult: async () => undefined,
		addToolOutput: async () => undefined,
		addToolApprovalResponse: async () => undefined,
		stop: async () => undefined,
		sendMessage: async () => undefined,
	}),
}));

function stubFetch(meStatus: 200 | 401) {
	vi.stubGlobal(
		"fetch",
		vi.fn().mockImplementation((input: RequestInfo | URL) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url.includes("/api/auth/refresh")) {
				return Promise.resolve(new Response(null, { status: 401 }));
			}
			if (url === "/api/v1/me") {
				if (meStatus === 200) {
					return Promise.resolve(
						new Response(JSON.stringify(TEST_USER), {
							status: 200,
							headers: { "Content-Type": "application/json" },
						}),
					);
				}
				return Promise.resolve(new Response(null, { status: 401 }));
			}
			return Promise.resolve(
				new Response(JSON.stringify({ items: [] }), {
					status: 200,
					headers: { "Content-Type": "application/json" },
				}),
			);
		}),
	);
}

function renderAt(initialPath: string) {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const router = createRouter({
		routeTree,
		history: createMemoryHistory({ initialEntries: [initialPath] }),
		context: { queryClient },
	});
	const result = render(
		<AuthProvider>
			<QueryClientProvider client={queryClient}>
				<RouterProvider router={router} />
			</QueryClientProvider>
		</AuthProvider>,
	);
	return { ...result, router };
}

describe("route guards — anonymous vs authed", () => {
	beforeEach(() => {
		stubFetch(401);
	});

	it("redirects an unauthenticated visitor from /app to /sign-in", async () => {
		const { router } = renderAt("/app");

		await waitFor(
			() => {
				expect(router.state.location.pathname).toBe("/sign-in");
			},
			{ timeout: 3000 },
		);
		expect(
			await screen.findByRole("heading", { name: /welcome back/i }),
		).toBeInTheDocument();
	});

	it("redirects an authenticated visitor from /sign-in to /app", async () => {
		stubFetch(200);
		const { router } = renderAt("/sign-in");

		await waitFor(
			() => {
				expect(router.state.location.pathname).toBe("/app");
			},
			{ timeout: 3000 },
		);
		expect(await screen.findByTestId("authed-shell")).toBeInTheDocument();
	});

	it("keeps an authenticated visitor on /app after session resolves", async () => {
		stubFetch(200);
		const { router } = renderAt("/app");

		expect(await screen.findByTestId("authed-shell")).toBeInTheDocument();
		expect(router.state.location.pathname).toBe("/app");
	});

	it("redirects an unauthenticated visitor from / to /sign-in", async () => {
		const { router } = renderAt("/");

		await waitFor(
			() => {
				expect(router.state.location.pathname).toBe("/sign-in");
			},
			{ timeout: 3000 },
		);
	});

	it("redirects an authenticated visitor from / to /app", async () => {
		stubFetch(200);
		const { router } = renderAt("/");

		await waitFor(
			() => {
				expect(router.state.location.pathname).toBe("/app");
			},
			{ timeout: 3000 },
		);
	});
});

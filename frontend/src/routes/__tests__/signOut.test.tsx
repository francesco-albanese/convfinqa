import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import { routeTree } from "@/routeTree.gen";

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

const TEST_USER = { user_id: "sign-out-test-user", email: "signout@test.com" };

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

beforeEach(() => {
	vi.stubGlobal(
		"fetch",
		vi.fn().mockImplementation((input: RequestInfo | URL) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url === "/api/v1/me") {
				return Promise.resolve(
					new Response(JSON.stringify(TEST_USER), {
						status: 200,
						headers: { "Content-Type": "application/json" },
					}),
				);
			}
			return Promise.resolve(new Response(null, { status: 200 }));
		}),
	);
});

describe("/_authed — sign out", () => {
	it("POSTs to /api/auth/logout and navigates to /sign-in", async () => {
		const fetchMock = vi.mocked(window.fetch);
		const user = userEvent.setup();
		const { router } = renderAt("/app");

		await screen.findByTestId("authed-shell", undefined, { timeout: 3000 });
		await user.click(screen.getByTestId("user-menu-trigger"));
		await user.click(
			await screen.findByRole("menuitem", { name: /sign out/i }),
		);

		await waitFor(() => {
			expect(router.state.location.pathname).toBe("/sign-in");
		});

		const logoutCall = fetchMock.mock.calls.find(([u]) =>
			String(u).includes("/api/auth/logout"),
		);
		expect(logoutCall).toBeDefined();
		expect(logoutCall?.[1]).toMatchObject({ method: "POST" });

		expect(
			await screen.findByRole("heading", { name: /welcome back/i }),
		).toBeInTheDocument();
	});

	it("shows pending feedback while the logout request is in flight", async () => {
		let finishLogout: (() => void) | undefined;
		vi.stubGlobal(
			"fetch",
			vi.fn().mockImplementation((input: RequestInfo | URL) => {
				const url = typeof input === "string" ? input : input.toString();
				if (url === "/api/v1/me") {
					return Promise.resolve(
						new Response(JSON.stringify(TEST_USER), {
							status: 200,
							headers: { "Content-Type": "application/json" },
						}),
					);
				}
				if (url.includes("/api/auth/logout")) {
					return new Promise<Response>((resolve) => {
						finishLogout = () => resolve(new Response(null, { status: 200 }));
					});
				}
				return Promise.resolve(new Response(null, { status: 200 }));
			}),
		);
		const user = userEvent.setup();
		renderAt("/app");

		await screen.findByTestId("authed-shell", undefined, { timeout: 3000 });
		await user.click(screen.getByTestId("user-menu-trigger"));
		await user.click(
			await screen.findByRole("menuitem", { name: /sign out/i }),
		);

		expect(screen.getByTestId("auth-loading-shell")).toBeInTheDocument();
		finishLogout?.();
	});
});

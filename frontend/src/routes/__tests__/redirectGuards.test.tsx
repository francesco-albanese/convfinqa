import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AUTH_STORAGE_KEY, AuthProvider } from "@/lib/auth/AuthProvider";
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
	it("redirects an unauthenticated visitor from /app to /sign-in", async () => {
		const { router } = renderAt("/app");

		await waitFor(() => {
			expect(router.state.location.pathname).toBe("/sign-in");
		});
		expect(
			await screen.findByRole("heading", { name: /welcome back/i }),
		).toBeInTheDocument();
	});

	it("redirects an authenticated visitor from /sign-in to /app", async () => {
		window.localStorage.setItem(AUTH_STORAGE_KEY, "dev-user-guard-test");

		const { router } = renderAt("/sign-in");

		await waitFor(() => {
			expect(router.state.location.pathname).toBe("/app");
		});
		expect(await screen.findByTestId("authed-shell")).toBeInTheDocument();
	});

	it("keeps an authenticated visitor on /app on a fresh load (storage hydrated synchronously)", async () => {
		window.localStorage.setItem(AUTH_STORAGE_KEY, "dev-user-reload-test");

		const { router } = renderAt("/app");

		expect(await screen.findByTestId("authed-shell")).toBeInTheDocument();
		expect(router.state.location.pathname).toBe("/app");
	});
});

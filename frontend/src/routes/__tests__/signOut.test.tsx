import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
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

beforeEach(() => {
	window.localStorage.setItem(AUTH_STORAGE_KEY, "dev-user-sign-out-test");
});

describe("/_authed — sign out", () => {
	it("clears the persisted user id and lands on /sign-in", async () => {
		const user = userEvent.setup();
		const { router } = renderAt("/app");

		await screen.findByTestId("authed-shell");
		await user.click(screen.getByTestId("user-menu-trigger"));
		await user.click(
			await screen.findByRole("menuitem", { name: /sign out/i }),
		);

		await waitFor(() => {
			expect(router.state.location.pathname).toBe("/sign-in");
		});
		expect(window.localStorage.getItem(AUTH_STORAGE_KEY)).toBeNull();
		expect(
			await screen.findByRole("heading", { name: /welcome back/i }),
		).toBeInTheDocument();
	});
});

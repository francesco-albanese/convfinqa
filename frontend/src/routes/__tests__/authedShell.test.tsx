import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

function renderApp(initialPath: string) {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const router = createRouter({
		routeTree,
		history: createMemoryHistory({ initialEntries: [initialPath] }),
		context: { queryClient },
	});
	return render(
		<QueryClientProvider client={queryClient}>
			<RouterProvider router={router} />
		</QueryClientProvider>,
	);
}

describe("/_authed layout — three-panel grid", () => {
	it("hides the right panel when no document is pinned", async () => {
		renderApp("/app");
		const shell = await screen.findByTestId("authed-shell");
		expect(shell).toHaveAttribute("data-right-panel", "closed");
		expect(screen.queryByLabelText("Pinned document")).not.toBeInTheDocument();
		expect(screen.getByLabelText("Sidebar")).toBeInTheDocument();
	});

	it("renders the right panel when documentId search param is set", async () => {
		renderApp("/app?documentId=single_NKE/2010/page_X");
		const shell = await screen.findByTestId("authed-shell");
		expect(shell).toHaveAttribute("data-right-panel", "open");
		expect(screen.getByLabelText("Pinned document")).toBeInTheDocument();
	});

	it("falls back to a closed shell when documentId is invalid", async () => {
		renderApp("/app?documentId=");
		const shell = await screen.findByTestId("authed-shell");
		expect(shell).toHaveAttribute("data-right-panel", "closed");
	});
});

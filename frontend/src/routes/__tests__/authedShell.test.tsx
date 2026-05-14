import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AUTH_STORAGE_KEY, AuthProvider } from "@/lib/auth/AuthProvider";
import type { DocumentListPage } from "@/lib/queries/documents";
import { setDocPickerOpen } from "@/lib/ui/docPickerStore";
import { setSidebarCollapsed } from "@/lib/ui/sidebarStore";
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
	window.localStorage.setItem(AUTH_STORAGE_KEY, "dev-user-authed-shell-test");
});

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

	it("reflects the sidebar collapsed state from the store", async () => {
		setSidebarCollapsed(true);
		try {
			renderApp("/app");
			const shell = await screen.findByTestId("authed-shell");
			expect(shell).toHaveAttribute("data-sidebar", "collapsed");
		} finally {
			setSidebarCollapsed(false);
		}
	});
});

describe("/_authed layout — DocPicker → navigation wire-up", () => {
	afterEach(() => {
		vi.unstubAllGlobals();
		setDocPickerOpen(false);
	});

	it("pins the document via documentId search param when a picker result is clicked", async () => {
		const page: DocumentListPage = {
			items: [
				{
					id: "Single_NKE/2010/page_28.pdf-3",
					ticker: "NKE",
					year: 2010,
					page: 28,
					title: "NKE 2010 page 28",
				},
			],
			next_cursor: null,
		};
		vi.stubGlobal(
			"fetch",
			vi.fn().mockResolvedValue(
				new Response(JSON.stringify(page), {
					status: 200,
					headers: { "Content-Type": "application/json" },
				}),
			),
		);
		const user = userEvent.setup();

		const { router } = renderApp("/app");
		setDocPickerOpen(true);

		const result = await screen.findByRole("option", {
			name: /nke 2010 page 28/i,
		});
		await user.click(result);

		await waitFor(() => {
			expect(router.state.location.search).toEqual({
				documentId: "Single_NKE/2010/page_28.pdf-3",
			});
		});
	});
});

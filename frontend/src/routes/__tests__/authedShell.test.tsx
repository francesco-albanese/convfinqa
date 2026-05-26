import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import type { DocumentListPage } from "@/lib/queries/documents";
import { setDocPickerOpen } from "@/lib/ui/docPickerStore";
import {
	closeRightPanelSheet,
	closeSidebarDrawer,
} from "@/lib/ui/responsiveStore";
import { setSidebarCollapsed } from "@/lib/ui/sidebarStore";
import { routeTree } from "@/routeTree.gen";

const TEST_USER = {
	user_id: "authed-shell-test-user",
	email: "test@example.com",
};

function meResponse() {
	return new Response(JSON.stringify(TEST_USER), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

function makeFetchWithMe(
	handler: (url: string) => Promise<Response> | Response,
) {
	return vi.fn().mockImplementation((input: RequestInfo | URL) => {
		const url = typeof input === "string" ? input : input.toString();
		if (url === "/api/v1/me") return Promise.resolve(meResponse());
		return handler(url);
	});
}

function installMatchMediaMock(belowLg: boolean): void {
	vi.stubGlobal(
		"matchMedia",
		vi.fn((query: string) => ({
			matches: query.includes("min-width: 1024px") ? !belowLg : false,
			media: query,
			addEventListener: () => {},
			removeEventListener: () => {},
			addListener: () => {},
			removeListener: () => {},
			dispatchEvent: () => true,
			onchange: null,
		})),
	);
}

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
	vi.stubGlobal(
		"fetch",
		makeFetchWithMe(() => Promise.resolve(new Response(null, { status: 404 }))),
	);
});

describe("/_authed layout — three-panel grid", () => {
	it("hides the right panel when no document is pinned", async () => {
		renderApp("/app");
		const shell = await screen.findByTestId("authed-shell", undefined, {
			timeout: 5000,
		});
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

describe("/_authed layout — drawer + sheet a11y (below lg)", () => {
	beforeEach(() => {
		installMatchMediaMock(true);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
		closeSidebarDrawer();
		closeRightPanelSheet();
	});

	it("marks the sidebar drawer as role=dialog with aria-modal when opened below lg", async () => {
		const user = userEvent.setup();
		renderApp("/app");
		await screen.findByTestId("authed-shell");
		const shell = screen.getByTestId("sidebar-shell");
		expect(shell).not.toHaveAttribute("role");

		await user.click(screen.getByTestId("sidebar-hamburger"));

		await waitFor(() => {
			expect(shell).toHaveAttribute("role", "dialog");
		});
		expect(shell).toHaveAttribute("aria-modal", "true");
		expect(shell).toHaveAttribute("aria-label", "Sidebar drawer");
	});

	it("closes the sidebar drawer when Escape is pressed and returns focus to the hamburger", async () => {
		const user = userEvent.setup();
		renderApp("/app");
		const shell = await screen.findByTestId("authed-shell");
		const hamburger = screen.getByTestId("sidebar-hamburger");

		await user.click(hamburger);
		await waitFor(() => {
			expect(shell).toHaveAttribute("data-drawer", "open");
		});

		await user.keyboard("{Escape}");

		await waitFor(() => {
			expect(shell).toHaveAttribute("data-drawer", "closed");
		});
		expect(hamburger).toHaveFocus();
	});

	it("closes the open sidebar drawer when New conversation resets the chat", async () => {
		const user = userEvent.setup();
		const { router } = renderApp("/app?documentId=doc-1&chatId=conv-7");
		const shell = await screen.findByTestId("authed-shell");

		await user.click(screen.getByTestId("sidebar-hamburger"));
		await waitFor(() => {
			expect(shell).toHaveAttribute("data-drawer", "open");
		});

		await user.click(screen.getByRole("button", { name: "New conversation" }));

		await waitFor(() => {
			expect(shell).toHaveAttribute("data-drawer", "closed");
		});
		expect(router.state.location.href).toBe("/app");
	});

	it("marks the right-panel sheet as role=dialog and closes via Escape", async () => {
		const documentBody = {
			id: "Single_NKE/2010/page_28.pdf-3",
			ticker: "NKE",
			year: 2010,
			page: 28,
			title: "NKE 2010 page 28",
			pre_text: null,
			post_text: null,
			column_order: null,
			table_data: null,
		};
		vi.stubGlobal(
			"fetch",
			makeFetchWithMe(() =>
				Promise.resolve(
					new Response(JSON.stringify(documentBody), {
						status: 200,
						headers: { "Content-Type": "application/json" },
					}),
				),
			),
		);
		installMatchMediaMock(true);
		const user = userEvent.setup();

		renderApp("/app?documentId=Single_NKE/2010/page_28.pdf-3");
		const shell = await screen.findByTestId("authed-shell");
		const viewDoc = await screen.findByTestId("view-document-button");

		await user.click(viewDoc);
		await waitFor(() => {
			expect(shell).toHaveAttribute("data-sheet", "open");
		});
		const panel = screen.getByTestId("right-panel");
		expect(panel).toHaveAttribute("role", "dialog");
		expect(panel).toHaveAttribute("aria-modal", "true");

		await user.keyboard("{Escape}");

		await waitFor(() => {
			expect(shell).toHaveAttribute("data-sheet", "closed");
		});
		expect(viewDoc).toHaveFocus();
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
			makeFetchWithMe((url) => {
				const body = url.startsWith("/api/v1/chats") ? { items: [] } : page;
				return Promise.resolve(
					new Response(JSON.stringify(body), {
						status: 200,
						headers: { "Content-Type": "application/json" },
					}),
				);
			}),
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

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

const TEST_USER = { user_id: "delete-test-user", email: "delete@test.com" };

const CONV_A = "conv-a";
const CONV_B = "conv-b";

function chatSummary(id: string, title: string) {
	return {
		id,
		document: { id: "doc-1", ticker: "AAA", year: 2024, title: "AAA 2024" },
		last_message_preview: "preview",
		last_message_at: "2026-05-14T08:00:00+00:00",
		title,
	};
}

function jsonResponse(body: unknown): Response {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

function stubFetch() {
	const deleted: string[] = [];
	const fetchMock = vi
		.fn()
		.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url === "/api/v1/me") return Promise.resolve(jsonResponse(TEST_USER));
			if (url === "/api/v1/chats" && (!init || init.method === undefined)) {
				const items = [
					chatSummary(CONV_A, "Conversation A"),
					chatSummary(CONV_B, "Conversation B"),
				].filter((item) => !deleted.includes(item.id));
				return Promise.resolve(jsonResponse({ items }));
			}
			if (init?.method === "DELETE") {
				const id = url.split("/").pop() ?? "";
				deleted.push(decodeURIComponent(id));
				return Promise.resolve(new Response(null, { status: 204 }));
			}
			if (url.includes("/messages")) {
				return Promise.resolve(jsonResponse({ items: [] }));
			}
			return Promise.resolve(new Response(null, { status: 200 }));
		});
	vi.stubGlobal("fetch", fetchMock);
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

async function confirmDeleteOf(label: string) {
	const user = userEvent.setup();
	const deleteButton = await screen.findByRole("button", {
		name: `Delete conversation: ${label}`,
	});
	await user.click(deleteButton);
	const dialog = await screen.findByRole("dialog");
	await user.click(within(dialog).getByRole("button", { name: "Delete" }));
}

describe("/_authed — delete conversation", () => {
	beforeEach(() => {
		stubFetch();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it("deleting the active conversation resets to empty /app", async () => {
		const { router } = renderAt(`/app?chatId=${CONV_A}&documentId=doc-1`);
		await screen.findByTestId("authed-shell", undefined, { timeout: 3000 });

		await confirmDeleteOf("Conversation A");

		await waitFor(() => {
			expect(router.state.location.search).toEqual({});
		});
		expect(router.state.location.pathname).toBe("/app");
	});

	it("deleting a non-active conversation leaves the current view untouched", async () => {
		const { router } = renderAt(`/app?chatId=${CONV_A}&documentId=doc-1`);
		await screen.findByTestId("authed-shell", undefined, { timeout: 3000 });

		await confirmDeleteOf("Conversation B");

		await waitFor(() => {
			expect(
				screen.queryByRole("button", {
					name: "Delete conversation: Conversation B",
				}),
			).not.toBeInTheDocument();
		});
		expect(router.state.location.search).toEqual({
			chatId: CONV_A,
			documentId: "doc-1",
		});
	});
});

import type { UseChatHelpers } from "@ai-sdk/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ChatStatus, UIMessage } from "ai";
import { act, useEffect, useRef, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import { routeTree } from "@/routeTree.gen";

type DataPart = { type: string; data?: unknown };

type StreamScript = {
	conversationId?: string;
	assistantText?: string;
};

const streamScript: StreamScript = {};

function resetStreamScript() {
	streamScript.conversationId = undefined;
	streamScript.assistantText = undefined;
}

vi.mock("@/lib/chat/useConvfinqaChat", () => {
	return {
		useConvfinqaChat: (options: {
			onData?: (part: DataPart) => void;
			onFinish?: () => void;
		}): UseChatHelpers<UIMessage> => {
			const optionsRef = useRef(options);
			optionsRef.current = options;
			const [messages, setMessages] = useState<UIMessage[]>([]);
			const [status, setStatus] = useState<ChatStatus>("ready");
			useEffect(() => {
				return () => resetStreamScript();
			}, []);
			const sendMessage = async (input: { text: string }) => {
				setStatus("submitted");
				setMessages((prev) => [
					...prev,
					{
						id: `user-${prev.length}`,
						role: "user",
						parts: [{ type: "text", text: input.text }],
					},
				]);
				if (streamScript.conversationId) {
					optionsRef.current.onData?.({
						type: "data-conversation",
						data: { conversationId: streamScript.conversationId },
					});
				}
				if (streamScript.assistantText) {
					setMessages((prev) => [
						...prev,
						{
							id: `assistant-${prev.length}`,
							role: "assistant",
							parts: [{ type: "text", text: streamScript.assistantText ?? "" }],
						},
					]);
				}
				setStatus("ready");
				optionsRef.current.onFinish?.();
			};
			const stop = async () => {
				setStatus("ready");
			};
			return {
				id: "test-chat",
				messages,
				status,
				setMessages,
				error: undefined,
				clearError: () => undefined,
				resumeStream: async () => undefined,
				regenerate: async () => undefined,
				addToolResult: async () => undefined,
				addToolOutput: async () => undefined,
				addToolApprovalResponse: async () => undefined,
				stop,
				sendMessage,
			} as unknown as UseChatHelpers<UIMessage>;
		},
	};
});

function renderApp(initialPath: string) {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const invalidate = vi.spyOn(queryClient, "invalidateQueries");
	const router = createRouter({
		routeTree,
		history: createMemoryHistory({ initialEntries: [initialPath] }),
		context: { queryClient },
	});
	const utils = render(
		<AuthProvider>
			<QueryClientProvider client={queryClient}>
				<RouterProvider router={router} />
			</QueryClientProvider>
		</AuthProvider>,
	);
	return { ...utils, router, queryClient, invalidate };
}

type ChatsFetchOverrides = {
	chatList?: unknown;
	chatMessagesByChatId?: Record<string, unknown>;
	documentById?: Record<string, unknown>;
};

const APP_TEST_USER = { user_id: "app-test-user", email: "app@test.com" };

function stubChatsFetch(overrides: ChatsFetchOverrides = {}) {
	const fetchMock = vi
		.fn()
		.mockImplementation((input: RequestInfo | URL): Promise<Response> => {
			const url = typeof input === "string" ? input : input.toString();
			if (url === "/api/v1/me") {
				return Promise.resolve(
					new Response(JSON.stringify(APP_TEST_USER), {
						status: 200,
						headers: { "Content-Type": "application/json" },
					}),
				);
			}
			if (url.startsWith("/api/v1/documents/")) {
				const docId = decodeURIComponent(
					url.slice("/api/v1/documents/".length).split("?")[0] ?? "",
				);
				const document = overrides.documentById?.[docId];
				if (!document) {
					return Promise.resolve(new Response("{}", { status: 404 }));
				}
				return Promise.resolve(
					new Response(JSON.stringify(document), {
						status: 200,
						headers: { "Content-Type": "application/json" },
					}),
				);
			}
			if (url.startsWith("/api/v1/chats/")) {
				const match = url.match(/^\/api\/v1\/chats\/([^/]+)\/messages/);
				const chatId = match ? decodeURIComponent(match[1] ?? "") : "";
				const payload = overrides.chatMessagesByChatId?.[chatId] ?? {
					items: [],
				};
				return Promise.resolve(
					new Response(JSON.stringify(payload), {
						status: 200,
						headers: { "Content-Type": "application/json" },
					}),
				);
			}
			if (url.startsWith("/api/v1/chats")) {
				return Promise.resolve(
					new Response(JSON.stringify(overrides.chatList ?? { items: [] }), {
						status: 200,
						headers: { "Content-Type": "application/json" },
					}),
				);
			}
			return Promise.resolve(
				new Response("{}", {
					status: 200,
					headers: { "Content-Type": "application/json" },
				}),
			);
		});
	vi.stubGlobal("fetch", fetchMock);
	return fetchMock;
}

beforeEach(() => {
	resetStreamScript();
	stubChatsFetch();
});

afterEach(() => {
	resetStreamScript();
	vi.unstubAllGlobals();
});

describe("/app route — Composer + MessageList + useChat wiring", () => {
	it("renders the composer enabled when a documentId is in the search params", async () => {
		renderApp("/app?documentId=single_NKE/2010/page_X");
		const textarea = await screen.findByLabelText("Message", undefined, {
			timeout: 3000,
		});
		expect(textarea).not.toBeDisabled();
		expect(screen.getByText(/Pinned: single_NKE/)).toBeInTheDocument();
	});

	it("disables the composer with a hint when no document is pinned", async () => {
		renderApp("/app");
		const textarea = await screen.findByLabelText("Message");
		expect(textarea).toBeDisabled();
		expect(screen.getByRole("note")).toHaveTextContent("Pin a document first");
	});

	it("seeds the conversation with persisted messages when mounted with chatId in URL", async () => {
		stubChatsFetch({
			chatMessagesByChatId: {
				"conv-resume": {
					items: [
						{
							id: "m1",
							role: "user",
							content: "what was the revenue in 2009?",
							created_at: "2026-05-14T08:00:00+00:00",
						},
						{
							id: "m2",
							role: "assistant",
							content: "Revenue rose to $1.2B in 2009.",
							created_at: "2026-05-14T08:00:01+00:00",
						},
					],
				},
			},
		});
		renderApp("/app?chatId=conv-resume&documentId=doc-1");
		expect(
			await screen.findByText("what was the revenue in 2009?"),
		).toBeInTheDocument();
		expect(
			await screen.findByText("Revenue rose to $1.2B in 2009."),
		).toBeInTheDocument();
	});

	it("after Cmd+Enter, shows the user bubble, pulls chatId into the URL, and refreshes the chats query", async () => {
		streamScript.conversationId = "conv-7";
		streamScript.assistantText = "Revenue rose to $1.2B in 2009.";
		const user = userEvent.setup();
		const { router, invalidate } = renderApp("/app?documentId=doc-1");
		const textarea = await screen.findByLabelText("Message");
		await user.click(textarea);
		await user.type(textarea, "what was the revenue in 2009?");
		await act(async () => {
			await user.keyboard("{Meta>}{Enter}{/Meta}");
		});
		expect(
			await screen.findByText("what was the revenue in 2009?"),
		).toBeInTheDocument();
		await waitFor(() => {
			expect(router.state.location.search).toMatchObject({
				chatId: "conv-7",
				documentId: "doc-1",
			});
		});
		await waitFor(() => {
			expect(invalidate).toHaveBeenCalledWith({ queryKey: ["chats"] });
		});
	});

	it("unpin button clears documentId and chatId from the URL", async () => {
		const user = userEvent.setup();
		const { router } = renderApp("/app?documentId=doc-1&chatId=conv-7");
		const unpinButton = await screen.findByTestId("unpin-button");
		await user.click(unpinButton);
		await waitFor(() => {
			expect(router.state.location.href).toBe("/app");
		});
	});

	it("unpin button is not rendered when no document is pinned", async () => {
		renderApp("/app");
		await screen.findByLabelText("Message");
		expect(screen.queryByTestId("unpin-button")).not.toBeInTheDocument();
	});

	it("shows suggested-question pills for a pinned empty chat, then hides them after sending", async () => {
		const question = "what is the net cash from operating activities in 2009?";
		stubChatsFetch({
			documentById: {
				"doc-1": {
					id: "doc-1",
					ticker: "JKHY",
					year: 2009,
					page: 28,
					title: "JKHY 2009 annual report",
					pre_text: "",
					post_text: "",
					table_data: null,
					column_order: null,
					conv_questions: [question, "what about in 2008?"],
				},
			},
		});
		const user = userEvent.setup();
		renderApp("/app?documentId=doc-1");

		const pill = await screen.findByRole("button", { name: question });
		expect(pill).toBeInTheDocument();

		await act(async () => {
			await user.click(pill);
		});

		expect(screen.queryByTestId("suggested-questions")).not.toBeInTheDocument();
	});
});

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
import { setDocPickerOpen } from "@/lib/ui/docPickerStore";
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
	const refetch = vi.spyOn(queryClient, "refetchQueries");
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
	return { ...utils, router, queryClient, refetch };
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
			if (url.startsWith("/api/v1/documents")) {
				return Promise.resolve(
					new Response(
						JSON.stringify({
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
						}),
						{
							status: 200,
							headers: { "Content-Type": "application/json" },
						},
					),
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

	it("replays persisted assistant parts in backend order", async () => {
		stubChatsFetch({
			chatMessagesByChatId: {
				"conv-trace": {
					items: [
						{
							id: "m1",
							role: "assistant",
							content: "ignored when parts are present",
							created_at: "2026-05-14T08:00:01+00:00",
							parts: {
								schema_version: 1,
								parts: [
									{
										kind: "tool_call",
										call_id: "call-1",
										name: "divide",
										args: '{"a":"10","b":"2"}',
									},
									{
										kind: "tool_result",
										call_id: "call-1",
										is_error: false,
										result: '{"result":"5"}',
									},
									{ kind: "text", content: "Answer segment." },
									{
										kind: "citation",
										row_label: "long-term debt",
										col_label: "total",
									},
								],
							},
						},
					],
				},
			},
		});

		renderApp("/app?chatId=conv-trace&documentId=doc-1");

		const tool = await screen.findByTestId("tool-step");
		const answer = await screen.findByText("Answer segment.");
		const citation = await screen.findByTestId("citation-chip");

		expect(tool.compareDocumentPosition(answer)).toBe(
			Node.DOCUMENT_POSITION_FOLLOWING,
		);
		expect(answer.compareDocumentPosition(citation)).toBe(
			Node.DOCUMENT_POSITION_FOLLOWING,
		);
	});

	it("after Cmd+Enter, shows the user bubble, pulls chatId into the URL, and refreshes the chats query", async () => {
		streamScript.conversationId = "conv-7";
		streamScript.assistantText = "Revenue rose to $1.2B in 2009.";
		const user = userEvent.setup();
		const { router, refetch } = renderApp("/app?documentId=doc-1");
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
			expect(refetch).toHaveBeenCalledWith({
				queryKey: ["chats"],
				type: "active",
			});
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

	it("unpin clears the on-screen conversation and lands on empty /app", async () => {
		streamScript.assistantText = "Revenue rose to $1.2B in 2009.";
		const user = userEvent.setup();
		const { router } = renderApp("/app?documentId=doc-1&chatId=conv-7");
		const textarea = await screen.findByLabelText("Message");
		await user.type(textarea, "what was the revenue?");
		await act(async () => {
			await user.keyboard("{Meta>}{Enter}{/Meta}");
		});
		expect(
			await screen.findByText("Revenue rose to $1.2B in 2009."),
		).toBeInTheDocument();

		await user.click(screen.getByTestId("unpin-button"));

		await waitFor(() => {
			expect(router.state.location.href).toBe("/app");
		});
		expect(
			screen.queryByText("Revenue rose to $1.2B in 2009."),
		).not.toBeInTheDocument();
	});

	it("clicking the logo clears the conversation and unpins the document", async () => {
		streamScript.assistantText = "Revenue rose to $1.2B in 2009.";
		const user = userEvent.setup();
		const { router } = renderApp("/app?documentId=doc-1&chatId=conv-7");
		const textarea = await screen.findByLabelText("Message");
		await user.type(textarea, "what was the revenue?");
		await act(async () => {
			await user.keyboard("{Meta>}{Enter}{/Meta}");
		});
		expect(
			await screen.findByText("Revenue rose to $1.2B in 2009."),
		).toBeInTheDocument();

		await user.click(screen.getByTestId("reset-logo-button"));

		await waitFor(() => {
			expect(router.state.location.href).toBe("/app");
		});
		expect(
			screen.queryByText("Revenue rose to $1.2B in 2009."),
		).not.toBeInTheDocument();
	});

	it("New conversation clears the on-screen messages and unpins the document", async () => {
		streamScript.assistantText = "Revenue rose to $1.2B in 2009.";
		const user = userEvent.setup();
		const { router } = renderApp("/app?documentId=doc-1&chatId=conv-7");
		const textarea = await screen.findByLabelText("Message");
		await user.type(textarea, "what was the revenue?");
		await act(async () => {
			await user.keyboard("{Meta>}{Enter}{/Meta}");
		});
		expect(
			await screen.findByText("Revenue rose to $1.2B in 2009."),
		).toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "New conversation" }));

		await waitFor(() => {
			expect(router.state.location.href).toBe("/app");
		});
		expect(
			screen.queryByText("Revenue rose to $1.2B in 2009."),
		).not.toBeInTheDocument();
	});

	it("changing the document wipes the conversation and pins the new document", async () => {
		streamScript.assistantText = "Revenue rose to $1.2B in 2009.";
		const user = userEvent.setup();
		const { router } = renderApp("/app?documentId=doc-1&chatId=conv-7");
		const textarea = await screen.findByLabelText("Message");
		await user.type(textarea, "what was the revenue?");
		await act(async () => {
			await user.keyboard("{Meta>}{Enter}{/Meta}");
		});
		expect(
			await screen.findByText("Revenue rose to $1.2B in 2009."),
		).toBeInTheDocument();

		act(() => {
			setDocPickerOpen(true);
		});
		const result = await screen.findByRole("option", {
			name: /nke 2010 page 28/i,
		});
		await user.click(result);

		await waitFor(() => {
			expect(router.state.location.search).toEqual({
				documentId: "Single_NKE/2010/page_28.pdf-3",
			});
		});
		expect(
			screen.queryByText("Revenue rose to $1.2B in 2009."),
		).not.toBeInTheDocument();
	});

	it("prefills the composer from a suggested pill without sending, then offers the remaining question as a follow-up once a turn completes", async () => {
		const firstQuestion =
			"what is the net cash from operating activities in 2009?";
		const secondQuestion = "what about in 2008?";
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
					conv_questions: [firstQuestion, secondQuestion],
				},
			},
		});
		streamScript.assistantText =
			"Net cash from operating activities was $206m.";
		const user = userEvent.setup();
		renderApp("/app?documentId=doc-1");

		const pill = await screen.findByRole("button", { name: firstQuestion });
		await act(async () => {
			await user.click(pill);
		});

		const textarea = screen.getByRole("textbox", { name: /message/i });
		expect(textarea).toHaveValue(firstQuestion);
		expect(screen.getByTestId("suggested-questions")).toBeInTheDocument();

		await act(async () => {
			await user.keyboard("{Meta>}{Enter}{/Meta}");
		});

		expect(
			screen.queryByRole("button", { name: firstQuestion }),
		).not.toBeInTheDocument();
		expect(screen.getByText("try next")).toBeVisible();
		expect(
			screen.getByRole("button", { name: secondQuestion }),
		).toBeInTheDocument();
	});
});

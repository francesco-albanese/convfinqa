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
import { AUTH_STORAGE_KEY, AuthProvider } from "@/lib/auth/AuthProvider";
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

beforeEach(() => {
	resetStreamScript();
	window.localStorage.setItem(AUTH_STORAGE_KEY, "dev-user-app-test");
});

afterEach(() => {
	resetStreamScript();
});

describe("/app route — Composer + MessageList + useChat wiring", () => {
	it("renders the composer enabled when a documentId is in the search params", async () => {
		renderApp("/app?documentId=single_NKE/2010/page_X");
		const textarea = await screen.findByLabelText("Message");
		expect(textarea).not.toBeDisabled();
		expect(screen.getByText(/Pinned: single_NKE/)).toBeInTheDocument();
	});

	it("disables the composer with a hint when no document is pinned", async () => {
		renderApp("/app");
		const textarea = await screen.findByLabelText("Message");
		expect(textarea).toBeDisabled();
		expect(screen.getByRole("note")).toHaveTextContent("Pin a document first");
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
});

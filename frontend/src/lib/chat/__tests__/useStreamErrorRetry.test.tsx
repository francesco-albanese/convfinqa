import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { UIMessage } from "ai";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AUTH_STORAGE_KEY, AuthProvider } from "@/lib/auth/AuthProvider";
import {
	type UseStreamErrorRetryOptions,
	useStreamErrorRetry,
} from "@/lib/chat/useStreamErrorRetry";
import type { ChatMessageList } from "@/lib/queries/chats";

const TEST_USER_ID = "dev-user-test";
const CHAT_ID = "conv_42";

function jsonResponse(body: unknown): Response {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

function withProviders(client?: QueryClient): {
	wrapper: (props: { children: ReactNode }) => ReactNode;
	client: QueryClient;
} {
	window.localStorage.setItem(AUTH_STORAGE_KEY, TEST_USER_ID);
	const queryClient =
		client ??
		new QueryClient({ defaultOptions: { queries: { retry: false } } });
	return {
		client: queryClient,
		wrapper: ({ children }) =>
			createElement(
				QueryClientProvider,
				{ client: queryClient },
				createElement(AuthProvider, null, children),
			),
	};
}

function userMessage(id: string, text: string): UIMessage {
	return { id, role: "user", parts: [{ type: "text", text }] };
}

function makeConcurrentError(): Error {
	return new Error(JSON.stringify({ status: 409, title: "Conversation busy" }));
}

function makeServerError(): Error {
	return new Error(JSON.stringify({ status: 500, title: "boom" }));
}

type ChatStub = UseStreamErrorRetryOptions["chat"];

function chatStub(overrides: Partial<ChatStub> = {}): ChatStub {
	return {
		error: makeServerError(),
		messages: [userMessage("u1", "show me revenue")],
		sendMessage: vi.fn().mockResolvedValue(undefined),
		clearError: vi.fn(),
		...overrides,
	};
}

afterEach(() => {
	vi.restoreAllMocks();
});

describe("useStreamErrorRetry", () => {
	it("retry resends the last user message", async () => {
		const sendMessage = vi.fn().mockResolvedValue(undefined);
		const chat = chatStub({ sendMessage });
		const { wrapper } = withProviders();

		const { result } = renderHook(
			() => useStreamErrorRetry({ chat, chatId: CHAT_ID }),
			{ wrapper },
		);

		await act(async () => {
			await result.current.retry();
		});

		expect(sendMessage).toHaveBeenCalledExactlyOnceWith({
			text: "show me revenue",
		});
		expect(chat.clearError).toHaveBeenCalled();
	});

	it("does nothing when there is no prior user message", async () => {
		const sendMessage = vi.fn().mockResolvedValue(undefined);
		const chat = chatStub({ sendMessage, messages: [] });
		const { wrapper } = withProviders();

		const { result } = renderHook(
			() => useStreamErrorRetry({ chat, chatId: CHAT_ID }),
			{ wrapper },
		);

		await act(async () => {
			await result.current.retry();
		});

		expect(sendMessage).not.toHaveBeenCalled();
	});

	it("dismiss clears the chat error", () => {
		const chat = chatStub();
		const { wrapper } = withProviders();

		const { result } = renderHook(
			() => useStreamErrorRetry({ chat, chatId: CHAT_ID }),
			{ wrapper },
		);

		act(() => {
			result.current.dismiss();
		});

		expect(chat.clearError).toHaveBeenCalledOnce();
	});

	it("on a 409 retry waits until the messages query reports a growing list before sending", async () => {
		const fetchMock = vi.fn();
		const initial: ChatMessageList = {
			items: [
				{
					id: "u1",
					role: "user",
					content: "show me revenue",
					created_at: "2026-05-14T12:00:00.000Z",
				},
			],
		};
		const grown: ChatMessageList = {
			items: [
				...initial.items,
				{
					id: "a1",
					role: "assistant",
					content: "Revenue was X.",
					created_at: "2026-05-14T12:00:05.000Z",
				},
			],
		};
		fetchMock
			.mockResolvedValueOnce(jsonResponse(initial))
			.mockResolvedValueOnce(jsonResponse(grown));
		vi.stubGlobal("fetch", fetchMock);

		let resolveSend: () => void = () => undefined;
		const sendMessage = vi.fn(
			() =>
				new Promise<void>((resolve) => {
					resolveSend = resolve;
				}),
		);
		const chat = chatStub({
			sendMessage,
			error: makeConcurrentError(),
		});

		const { wrapper, client } = withProviders();
		client.setQueryData(["chats", "messages", CHAT_ID] as const, initial);

		const { result } = renderHook(
			() =>
				useStreamErrorRetry({
					chat,
					chatId: CHAT_ID,
					maxPollAttempts: 5,
					pollIntervalMs: 20,
				}),
			{ wrapper },
		);

		let retryPromise: Promise<void> | null = null;
		act(() => {
			retryPromise = result.current.retry();
		});

		await waitFor(() => {
			expect(fetchMock).toHaveBeenCalledTimes(1);
		});
		expect(sendMessage).not.toHaveBeenCalled();

		await waitFor(() => {
			expect(fetchMock).toHaveBeenCalledTimes(2);
		});

		await waitFor(() => {
			expect(sendMessage).toHaveBeenCalledExactlyOnceWith({
				text: "show me revenue",
			});
		});

		resolveSend();
		await act(async () => {
			await retryPromise;
		});
	});

	it("flips isRetrying while retry is in-flight", async () => {
		let resolveSend: () => void = () => undefined;
		const sendMessage = vi.fn(
			() =>
				new Promise<void>((resolve) => {
					resolveSend = resolve;
				}),
		);
		const chat = chatStub({ sendMessage });
		const { wrapper } = withProviders();

		const { result } = renderHook(
			() => useStreamErrorRetry({ chat, chatId: CHAT_ID }),
			{ wrapper },
		);

		let retryPromise: Promise<void> | null = null;
		act(() => {
			retryPromise = result.current.retry();
		});

		await waitFor(() => {
			expect(result.current.isRetrying).toBe(true);
		});

		resolveSend();
		await act(async () => {
			await retryPromise;
		});

		expect(result.current.isRetrying).toBe(false);
	});
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AUTH_STORAGE_KEY, AuthProvider } from "@/lib/auth/AuthProvider";
import {
	buildChatListUrl,
	buildChatMessagesUrl,
	type ChatList,
	ChatListSchema,
	type ChatMessageList,
	ChatMessageListSchema,
	type ChatSummary,
	useChatList,
	useChatMessages,
} from "@/lib/queries/chats";

const TEST_USER_ID = "dev-user-test";

function jsonResponse(body: unknown): Response {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

function withProviders(): {
	wrapper: (props: { children: ReactNode }) => ReactNode;
} {
	window.localStorage.setItem(AUTH_STORAGE_KEY, TEST_USER_ID);
	const client = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return {
		wrapper: ({ children }) =>
			createElement(
				QueryClientProvider,
				{ client },
				createElement(AuthProvider, null, children),
			),
	};
}

function headerValue(call: unknown[] | undefined, name: string): string | null {
	const init = call?.[1] as RequestInit | undefined;
	const headers = init?.headers as Record<string, string> | undefined;
	return headers?.[name] ?? null;
}

describe("buildChatListUrl / buildChatMessagesUrl", () => {
	it("builds the list endpoint without query string", () => {
		expect(buildChatListUrl()).toBe("/v1/chats");
	});

	it("path-encodes the conversation id in the messages endpoint", () => {
		expect(buildChatMessagesUrl("conv_abc123")).toBe(
			"/v1/chats/conv_abc123/messages",
		);
		expect(buildChatMessagesUrl("with space/slash")).toBe(
			"/v1/chats/with%20space%2Fslash/messages",
		);
	});
});

describe("ChatListSchema", () => {
	it("parses the wire shape emitted by GET /v1/chats", () => {
		const payload = {
			items: [
				{
					id: "conv_abc",
					document: {
						id: "doc-aaa",
						ticker: "AAA",
						year: 2024,
						title: "AAA 2024",
					},
					last_message_preview: "Hello",
					last_message_at: "2026-05-14T08:00:00+00:00",
				},
			],
		};
		const parsed: ChatList = ChatListSchema.parse(payload);
		expect(parsed.items[0]?.document.id).toBe("doc-aaa");
		expect(parsed.items[0]?.last_message_at).toBe("2026-05-14T08:00:00+00:00");
	});

	it("rejects payloads missing the document title field", () => {
		const bad = {
			items: [
				{
					id: "conv_abc",
					document: { id: "d", ticker: "T", year: 2024 },
					last_message_preview: "x",
					last_message_at: "2026-05-14T08:00:00+00:00",
				},
			],
		};
		expect(() => ChatListSchema.parse(bad)).toThrow();
	});
});

describe("ChatMessageListSchema", () => {
	it("parses the wire shape emitted by GET /v1/chats/{id}/messages", () => {
		const payload: ChatMessageList = ChatMessageListSchema.parse({
			items: [
				{
					id: "m1",
					role: "user",
					content: "hi",
					created_at: "2026-05-14T08:00:00+00:00",
				},
				{
					id: "m2",
					role: "assistant",
					content: "hello",
					created_at: "2026-05-14T08:00:05+00:00",
				},
			],
		});
		expect(payload.items.map((m) => m.role)).toEqual(["user", "assistant"]);
	});
});

describe("useChatList", () => {
	afterEach(() => {
		vi.unstubAllGlobals();
		window.localStorage.clear();
	});

	it("requests /v1/chats with the X-User-Id header and parses the response", async () => {
		const list: ChatList = {
			items: [
				{
					id: "conv_abc",
					document: {
						id: "doc-aaa",
						ticker: "AAA",
						year: 2024,
						title: "AAA 2024",
					},
					last_message_preview: "Hello",
					last_message_at: "2026-05-14T08:00:00+00:00",
				},
			],
		};
		const fetchMock = vi.fn().mockResolvedValue(jsonResponse(list));
		vi.stubGlobal("fetch", fetchMock);

		const { result } = renderHook(() => useChatList(), {
			wrapper: withProviders().wrapper,
		});

		await waitFor(() => {
			expect(result.current.isSuccess).toBe(true);
		});

		expect(fetchMock.mock.calls[0]?.[0]).toBe("/v1/chats");
		expect(headerValue(fetchMock.mock.calls[0], "X-User-Id")).toBe(
			TEST_USER_ID,
		);
		expect(result.current.data?.items[0]?.id).toBe("conv_abc");
	});

	it("surfaces a non-2xx response as an error", async () => {
		const fetchMock = vi
			.fn()
			.mockResolvedValue(new Response("nope", { status: 401 }));
		vi.stubGlobal("fetch", fetchMock);

		const { result } = renderHook(() => useChatList(), {
			wrapper: withProviders().wrapper,
		});

		await waitFor(() => {
			expect(result.current.isError).toBe(true);
		});
	});
});

describe("useChatMessages", () => {
	afterEach(() => {
		vi.unstubAllGlobals();
		window.localStorage.clear();
	});

	it("fetches /v1/chats/{id}/messages with X-User-Id when a chatId is provided", async () => {
		const messages: ChatMessageList = {
			items: [
				{
					id: "m1",
					role: "user",
					content: "hi",
					created_at: "2026-05-14T08:00:00+00:00",
				},
			],
		};
		const fetchMock = vi.fn().mockResolvedValue(jsonResponse(messages));
		vi.stubGlobal("fetch", fetchMock);

		const { result } = renderHook(() => useChatMessages("conv_abc"), {
			wrapper: withProviders().wrapper,
		});

		await waitFor(() => {
			expect(result.current.isSuccess).toBe(true);
		});

		expect(fetchMock.mock.calls[0]?.[0]).toBe("/v1/chats/conv_abc/messages");
		expect(headerValue(fetchMock.mock.calls[0], "X-User-Id")).toBe(
			TEST_USER_ID,
		);
		expect(result.current.data?.items[0]?.content).toBe("hi");
	});

	it("stays idle when chatId is null", () => {
		const fetchMock = vi.fn();
		vi.stubGlobal("fetch", fetchMock);

		const { result } = renderHook(() => useChatMessages(null), {
			wrapper: withProviders().wrapper,
		});

		expect(fetchMock).not.toHaveBeenCalled();
		expect(result.current.fetchStatus).toBe("idle");
	});
});

describe("ChatSummary type inference", () => {
	it("infers a ChatSummary that matches the documented backend contract", () => {
		const summary: ChatSummary = {
			id: "conv_abc",
			document: {
				id: "doc-aaa",
				ticker: "AAA",
				year: 2024,
				title: "AAA 2024",
			},
			last_message_preview: "preview",
			last_message_at: "2026-05-14T08:00:00+00:00",
		};
		expect(summary.id).toBe("conv_abc");
	});
});

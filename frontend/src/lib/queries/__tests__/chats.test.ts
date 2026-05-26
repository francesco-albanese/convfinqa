import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "@/lib/auth/AuthProvider";
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

const TEST_USER = { user_id: "chats-test-user-uuid", email: "chats@test.com" };

function jsonResponse(body: unknown): Response {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

function withProviders(): {
	wrapper: (props: { children: ReactNode }) => ReactNode;
} {
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
		expect(buildChatListUrl()).toBe("/api/v1/chats");
	});

	it("path-encodes the conversation id in the messages endpoint", () => {
		expect(buildChatMessagesUrl("conv_abc123")).toBe(
			"/api/v1/chats/conv_abc123/messages",
		);
		expect(buildChatMessagesUrl("with space/slash")).toBe(
			"/api/v1/chats/with%20space%2Fslash/messages",
		);
	});
});

describe("ChatListSchema", () => {
	it("parses the wire shape emitted by GET /api/v1/chats", () => {
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
					title: "Revenue trend question",
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
	it("parses the wire shape emitted by GET /api/v1/chats/{id}/messages", () => {
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
	beforeEach(() => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockImplementation((input: RequestInfo | URL) => {
				const url = typeof input === "string" ? input : input.toString();
				if (url === "/api/v1/me")
					return Promise.resolve(jsonResponse(TEST_USER));
				return Promise.resolve(new Response(null, { status: 404 }));
			}),
		);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it("requests /api/v1/chats with the X-User-Id header and parses the response", async () => {
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
					title: null,
				},
			],
		};
		const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url === "/api/v1/me") return Promise.resolve(jsonResponse(TEST_USER));
			return Promise.resolve(jsonResponse(list));
		});
		vi.stubGlobal("fetch", fetchMock);

		const { result } = renderHook(() => useChatList(), {
			wrapper: withProviders().wrapper,
		});

		await waitFor(() => {
			expect(result.current.isSuccess).toBe(true);
		});

		const chatsCall = fetchMock.mock.calls.find(
			([u]) => String(u) === "/api/v1/chats",
		);
		expect(chatsCall).toBeDefined();
		expect(headerValue(chatsCall, "X-User-Id")).toBe(TEST_USER.user_id);
		expect(result.current.data?.items[0]?.id).toBe("conv_abc");
	});

	it("surfaces a non-2xx response as an error", async () => {
		const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url === "/api/v1/me") return Promise.resolve(jsonResponse(TEST_USER));
			return Promise.resolve(new Response("server error", { status: 500 }));
		});
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
	beforeEach(() => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockImplementation((input: RequestInfo | URL) => {
				const url = typeof input === "string" ? input : input.toString();
				if (url === "/api/v1/me")
					return Promise.resolve(jsonResponse(TEST_USER));
				return Promise.resolve(new Response(null, { status: 404 }));
			}),
		);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it("fetches /api/v1/chats/{id}/messages with X-User-Id when a chatId is provided", async () => {
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
		const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url === "/api/v1/me") return Promise.resolve(jsonResponse(TEST_USER));
			return Promise.resolve(jsonResponse(messages));
		});
		vi.stubGlobal("fetch", fetchMock);

		const { result } = renderHook(() => useChatMessages("conv_abc"), {
			wrapper: withProviders().wrapper,
		});

		await waitFor(() => {
			expect(result.current.isSuccess).toBe(true);
		});

		const messagesCall = fetchMock.mock.calls.find(
			([u]) => String(u) === "/api/v1/chats/conv_abc/messages",
		);
		expect(messagesCall).toBeDefined();
		expect(headerValue(messagesCall, "X-User-Id")).toBe(TEST_USER.user_id);
		expect(result.current.data?.items[0]?.content).toBe("hi");
	});

	it("stays idle when chatId is null", async () => {
		const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url === "/api/v1/me") return Promise.resolve(jsonResponse(TEST_USER));
			return Promise.resolve(new Response(null, { status: 404 }));
		});
		vi.stubGlobal("fetch", fetchMock);

		const { result } = renderHook(() => useChatMessages(null), {
			wrapper: withProviders().wrapper,
		});

		await waitFor(() => {
			expect(result.current.fetchStatus).toBe("idle");
		});

		const chatsCall = fetchMock.mock.calls.find(([u]) =>
			String(u).includes("/api/v1/chats/"),
		);
		expect(chatsCall).toBeUndefined();
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
			title: null,
		};
		expect(summary.id).toBe("conv_abc");
	});
});

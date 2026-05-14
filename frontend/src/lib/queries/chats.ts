import { skipToken, useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { useAuthedUserId } from "@/lib/auth/AuthProvider";

const IsoDatetime = z.iso.datetime({ offset: true });

export const ChatDocumentSchema = z.object({
	id: z.string().min(1),
	ticker: z.string().nullable(),
	year: z.number().int().nullable(),
	title: z.string().nullable(),
});

export const ChatSummarySchema = z.object({
	id: z.string().min(1),
	document: ChatDocumentSchema,
	last_message_preview: z.string(),
	last_message_at: IsoDatetime,
});

export const ChatListSchema = z.object({
	items: z.array(ChatSummarySchema),
});

export const ChatMessageSchema = z.object({
	id: z.string().min(1),
	role: z.string(),
	content: z.string(),
	created_at: IsoDatetime,
});

export const ChatMessageListSchema = z.object({
	items: z.array(ChatMessageSchema),
});

export type ChatDocument = z.infer<typeof ChatDocumentSchema>;
export type ChatSummary = z.infer<typeof ChatSummarySchema>;
export type ChatList = z.infer<typeof ChatListSchema>;
export type ChatMessage = z.infer<typeof ChatMessageSchema>;
export type ChatMessageList = z.infer<typeof ChatMessageListSchema>;

const CHATS_PATH = "/v1/chats";

export function buildChatListUrl(): string {
	return CHATS_PATH;
}

export function buildChatMessagesUrl(chatId: string): string {
	return `${CHATS_PATH}/${encodeURIComponent(chatId)}/messages`;
}

export function chatListQueryKey(userId: string) {
	return ["chats", "list", userId] as const;
}

export function chatMessagesQueryKey(chatId: string | null | undefined) {
	return ["chats", "messages", chatId ?? null] as const;
}

function authHeaders(userId: string): HeadersInit {
	return { Accept: "application/json", "X-User-Id": userId };
}

export async function fetchChatList(userId: string): Promise<ChatList> {
	const response = await fetch(buildChatListUrl(), {
		headers: authHeaders(userId),
	});
	if (!response.ok) {
		throw new Error(`fetchChatList: ${response.status} ${response.statusText}`);
	}
	return ChatListSchema.parse(await response.json());
}

export async function fetchChatMessages(
	chatId: string,
	userId: string,
): Promise<ChatMessageList> {
	const response = await fetch(buildChatMessagesUrl(chatId), {
		headers: authHeaders(userId),
	});
	if (!response.ok) {
		throw new Error(
			`fetchChatMessages: ${response.status} ${response.statusText}`,
		);
	}
	return ChatMessageListSchema.parse(await response.json());
}

export function useChatList() {
	const userId = useAuthedUserId();
	return useQuery({
		queryKey: chatListQueryKey(userId),
		queryFn: () => fetchChatList(userId),
	});
}

export function useChatMessages(chatId: string | null | undefined) {
	const userId = useAuthedUserId();
	return useQuery({
		queryKey: chatMessagesQueryKey(chatId),
		queryFn: chatId ? () => fetchChatMessages(chatId, userId) : skipToken,
		staleTime: Number.POSITIVE_INFINITY,
	});
}

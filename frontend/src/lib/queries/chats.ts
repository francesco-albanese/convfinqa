import { skipToken, useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { apiFetch } from "@/lib/api/client";
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

const StoredTextPartSchema = z.object({
	kind: z.literal("text"),
	content: z.string(),
});

const StoredReasoningPartSchema = z.object({
	kind: z.literal("reasoning"),
	id: z.string(),
	content: z.string(),
});

export const StoredToolCallPartSchema = z.object({
	kind: z.literal("tool_call"),
	call_id: z.string(),
	name: z.string(),
	args: z.string(),
});

export const StoredToolResultPartSchema = z.object({
	kind: z.literal("tool_result"),
	call_id: z.string(),
	is_error: z.boolean(),
	result: z.string(),
});

export const StoredCitationPartSchema = z.object({
	kind: z.literal("citation"),
	row_label: z.string(),
	col_label: z.string(),
});

const StoredPartSchema = z.discriminatedUnion("kind", [
	StoredTextPartSchema,
	StoredReasoningPartSchema,
	StoredToolCallPartSchema,
	StoredToolResultPartSchema,
	StoredCitationPartSchema,
]);

const MessagePartsEnvelopeSchema = z.object({
	schema_version: z.literal(1),
	parts: z.array(StoredPartSchema),
});

export const ChatMessageSchema = z.object({
	id: z.string().min(1),
	role: z.string(),
	content: z.string(),
	created_at: IsoDatetime,
	parts: MessagePartsEnvelopeSchema.nullable().optional(),
});

export const ChatMessageListSchema = z.object({
	items: z.array(ChatMessageSchema),
});

export type ChatDocument = z.infer<typeof ChatDocumentSchema>;
export type ChatSummary = z.infer<typeof ChatSummarySchema>;
export type ChatList = z.infer<typeof ChatListSchema>;
export type ChatMessage = z.infer<typeof ChatMessageSchema>;
export type ChatMessageList = z.infer<typeof ChatMessageListSchema>;
export type StoredPart = z.infer<typeof StoredPartSchema>;
export type MessagePartsEnvelope = z.infer<typeof MessagePartsEnvelopeSchema>;
export type StoredToolCallPart = z.infer<typeof StoredToolCallPartSchema>;
export type StoredToolResultPart = z.infer<typeof StoredToolResultPartSchema>;
export type StoredCitationPart = z.infer<typeof StoredCitationPartSchema>;

const CHATS_PATH = "/api/v1/chats";

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
	const response = await apiFetch(buildChatListUrl(), {
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
	const response = await apiFetch(buildChatMessagesUrl(chatId), {
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
		queryFn: userId ? () => fetchChatList(userId) : skipToken,
	});
}

export function useChatMessages(chatId: string | null | undefined) {
	const userId = useAuthedUserId();
	return useQuery({
		queryKey: chatMessagesQueryKey(chatId),
		queryFn:
			chatId && userId ? () => fetchChatMessages(chatId, userId) : skipToken,
		staleTime: Number.POSITIVE_INFINITY,
	});
}

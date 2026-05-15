import { DefaultChatTransport, type UIMessage } from "ai";
import { buildChatRequestBody } from "@/lib/transport/buildChatRequestBody";

export type CreateChatTransportOptions = {
	getUserId: () => string;
	getDocumentId: () => string | null;
	getConversationId: () => string | null;
};

export function createChatTransport(
	options: CreateChatTransportOptions,
): DefaultChatTransport<UIMessage> {
	return new DefaultChatTransport<UIMessage>({
		api: "/api/v1/chat/stream",
		headers: () => ({ "X-User-Id": options.getUserId() }),
		prepareSendMessagesRequest: ({ messages }) => ({
			body: buildChatRequestBody({
				messages,
				conversationId: options.getConversationId(),
				documentId: options.getDocumentId(),
			}),
		}),
	});
}

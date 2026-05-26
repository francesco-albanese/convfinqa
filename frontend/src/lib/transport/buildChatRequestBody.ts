import type { UIMessage } from "ai";

export type ChatRequestBody = {
	message: string;
	conversation_id?: string;
	document_id?: string;
	model?: string;
};

type BuildChatRequestBodyArgs = {
	messages: UIMessage[];
	conversationId: string | null;
	documentId: string | null;
	model?: string | null;
};

export function buildChatRequestBody({
	messages,
	conversationId,
	documentId,
	model,
}: BuildChatRequestBodyArgs): ChatRequestBody {
	const message = extractLatestUserText(messages);
	const modelField = model ? { model } : {};
	if (conversationId) {
		return { message, conversation_id: conversationId, ...modelField };
	}
	if (!documentId) {
		throw new Error(
			"createChatTransport: document_id is required when no conversation_id is known",
		);
	}
	return { message, document_id: documentId, ...modelField };
}

function extractLatestUserText(messages: UIMessage[]): string {
	const latest = messages.at(-1);
	if (!latest || latest.role !== "user") {
		throw new Error(
			"createChatTransport: expected the latest message to be a user message",
		);
	}
	const text = latest.parts
		.filter(
			(part): part is { type: "text"; text: string } => part.type === "text",
		)
		.map((part) => part.text)
		.join("");
	if (!text) {
		throw new Error(
			"createChatTransport: the latest user message has no text content",
		);
	}
	return text;
}

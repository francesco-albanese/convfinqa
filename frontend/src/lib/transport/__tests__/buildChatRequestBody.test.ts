import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { buildChatRequestBody } from "@/lib/transport/buildChatRequestBody";

function userMessage(text: string): UIMessage {
	return {
		id: "msg-1",
		role: "user",
		parts: [{ type: "text", text }],
	};
}

describe("buildChatRequestBody", () => {
	it("first turn: sends document_id and no conversation_id", () => {
		const body = buildChatRequestBody({
			messages: [userMessage("what was the revenue in 2009?")],
			conversationId: null,
			documentId: "single_NKE/2010/page_X",
		});

		expect(body).toEqual({
			message: "what was the revenue in 2009?",
			document_id: "single_NKE/2010/page_X",
		});
		expect(body).not.toHaveProperty("conversation_id");
	});

	it("subsequent turn: sends conversation_id and no document_id", () => {
		const body = buildChatRequestBody({
			messages: [userMessage("and 2008?")],
			conversationId: "conv-42",
			documentId: "single_NKE/2010/page_X",
		});

		expect(body).toEqual({
			message: "and 2008?",
			conversation_id: "conv-42",
		});
		expect(body).not.toHaveProperty("document_id");
	});

	it("throws when no conversation_id and no document_id", () => {
		expect(() =>
			buildChatRequestBody({
				messages: [userMessage("hello")],
				conversationId: null,
				documentId: null,
			}),
		).toThrow(/document_id is required/);
	});
});

import { describe, expect, it } from "vitest";
import { createChatTransport } from "@/lib/transport/createChatTransport";

type HeadersAccessor = { headers: () => Record<string, string> };

describe("createChatTransport headers callback", () => {
	it("reads the current user id on every invocation (no stale closure)", () => {
		let userId = "alice";
		const transport = createChatTransport({
			getUserId: () => userId,
			getDocumentId: () => "doc-1",
			getConversationId: () => null,
		});

		const headersFn = (transport as unknown as HeadersAccessor).headers;

		expect(headersFn()).toEqual({ "X-User-Id": "alice" });

		userId = "bob";
		expect(headersFn()).toEqual({ "X-User-Id": "bob" });
	});
});

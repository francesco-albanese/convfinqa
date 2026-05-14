import { describe, expect, it } from "vitest";
import { classifyStreamError } from "@/lib/chat/streamErrorClassifier";

describe("classifyStreamError", () => {
	it("returns null when there is no error", () => {
		expect(classifyStreamError(undefined)).toBeNull();
	});

	it("classifies a 409 problem+json body as 'concurrent'", () => {
		const error = new Error(
			JSON.stringify({
				type: "about:blank/conversation-busy",
				title: "Conversation busy",
				status: 409,
				detail: "Another request is already in flight.",
			}),
		);
		expect(classifyStreamError(error)).toBe("concurrent");
	});

	it("classifies a 500 problem+json body as 'server'", () => {
		const error = new Error(JSON.stringify({ status: 500, title: "boom" }));
		expect(classifyStreamError(error)).toBe("server");
	});

	it("classifies a TypeError (fetch failure) as 'network'", () => {
		const error = new TypeError("Failed to fetch");
		expect(classifyStreamError(error)).toBe("network");
	});

	it("classifies a generic 'Failed to fetch' as 'network' even when not a TypeError", () => {
		const error = new Error("Failed to fetch");
		expect(classifyStreamError(error)).toBe("network");
	});

	it("falls back to 'unknown' for a non-JSON stream error frame", () => {
		const error = new Error("provider exploded mid stream");
		expect(classifyStreamError(error)).toBe("unknown");
	});
});

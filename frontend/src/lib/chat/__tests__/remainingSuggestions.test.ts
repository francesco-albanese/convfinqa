import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { remainingSuggestions } from "@/lib/chat/remainingSuggestions";

const QUESTIONS = [
	"what was the net cash in 2009?",
	"what about in 2008?",
	"what is the percent change?",
];

function userMessage(text: string): UIMessage {
	return { id: text, role: "user", parts: [{ type: "text", text }] };
}

function assistantMessage(text: string): UIMessage {
	return {
		id: `a-${text}`,
		role: "assistant",
		parts: [{ type: "text", text }],
	};
}

describe("remainingSuggestions", () => {
	it("drops questions already asked verbatim, case-insensitively", () => {
		const messages = [
			userMessage("What Was The Net Cash In 2009?"),
			assistantMessage("It was $206m."),
		];

		expect(remainingSuggestions(QUESTIONS, messages)).toEqual([
			"what about in 2008?",
			"what is the percent change?",
		]);
	});

	it("keeps every question when none have been asked", () => {
		expect(remainingSuggestions(QUESTIONS, [])).toEqual(QUESTIONS);
	});

	it("ignores assistant messages when matching", () => {
		const messages = [assistantMessage("what about in 2008?")];

		expect(remainingSuggestions(QUESTIONS, messages)).toEqual(QUESTIONS);
	});
});

import type { TextUIPart, UIMessage } from "ai";

function userMessageText(message: UIMessage): string {
	return message.parts
		.filter((p): p is TextUIPart => p.type === "text")
		.map((p) => p.text)
		.join("")
		.trim();
}

export function remainingSuggestions(
	questions: ReadonlyArray<string>,
	messages: ReadonlyArray<UIMessage>,
): ReadonlyArray<string> {
	const asked = new Set(
		messages
			.filter((m) => m.role === "user")
			.map((m) => userMessageText(m).toLowerCase()),
	);
	return questions.filter((q) => !asked.has(q.trim().toLowerCase()));
}

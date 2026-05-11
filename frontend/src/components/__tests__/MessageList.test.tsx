import { render, screen } from "@testing-library/react";
import type { ChatStatus, UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { MessageList } from "@/components/MessageList";

function makeMessage(
	id: string,
	role: UIMessage["role"],
	text: string,
): UIMessage {
	return { id, role, parts: [{ type: "text", text }] };
}

function renderList(messages: UIMessage[], status: ChatStatus) {
	return render(<MessageList messages={messages} status={status} />);
}

describe("MessageList", () => {
	it("shows the pulsing cursor on the last assistant message while streaming and removes it when ready", () => {
		const messages = [
			makeMessage("u1", "user", "hi"),
			makeMessage("a1", "assistant", ""),
		];

		const { rerender } = renderList(messages, "streaming");
		expect(screen.getByTestId("streaming-cursor")).toBeInTheDocument();

		rerender(<MessageList messages={messages} status="ready" />);
		expect(screen.queryByTestId("streaming-cursor")).not.toBeInTheDocument();
	});

	it("does not put a cursor on prior assistant messages during a new turn", () => {
		const messages = [
			makeMessage("u1", "user", "first"),
			makeMessage("a1", "assistant", "old answer"),
			makeMessage("u2", "user", "second"),
			makeMessage("a2", "assistant", ""),
		];

		renderList(messages, "streaming");

		const cursors = screen.getAllByTestId("streaming-cursor");
		expect(cursors).toHaveLength(1);
	});
});

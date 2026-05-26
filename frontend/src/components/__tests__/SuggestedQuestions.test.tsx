import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SuggestedQuestions } from "@/components/SuggestedQuestions";

const QUESTIONS = [
	"what is the net cash from operating activities in 2009?",
	"what about in 2008?",
];

describe("SuggestedQuestions", () => {
	it("sends the clicked question verbatim", async () => {
		const user = userEvent.setup();
		const onSend = vi.fn();
		render(<SuggestedQuestions questions={QUESTIONS} onSend={onSend} />);

		await user.click(screen.getByRole("button", { name: QUESTIONS[1] }));

		expect(onSend).toHaveBeenCalledTimes(1);
		expect(onSend).toHaveBeenCalledWith(QUESTIONS[1]);
	});

	it("renders nothing when there are no questions", () => {
		const { container } = render(
			<SuggestedQuestions questions={[]} onSend={vi.fn()} />,
		);

		expect(container).toBeEmptyDOMElement();
	});
});

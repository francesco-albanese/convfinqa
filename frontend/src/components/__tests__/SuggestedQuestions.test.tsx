import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SuggestedQuestions } from "@/components/SuggestedQuestions";

const QUESTIONS = [
	"what is the net cash from operating activities in 2009?",
	"what about in 2008?",
];

describe("SuggestedQuestions", () => {
	it("hands the clicked question verbatim to onSelect", async () => {
		const user = userEvent.setup();
		const onSelect = vi.fn();
		render(<SuggestedQuestions questions={QUESTIONS} onSelect={onSelect} />);

		await user.click(screen.getByRole("button", { name: QUESTIONS[1] }));

		expect(onSelect).toHaveBeenCalledExactlyOnceWith(QUESTIONS[1]);
	});

	it("labels the follow-up variant 'try next'", () => {
		render(
			<SuggestedQuestions
				questions={QUESTIONS}
				onSelect={vi.fn()}
				variant="followup"
			/>,
		);

		expect(screen.getByText("try next")).toBeVisible();
	});

	it("renders nothing when there are no questions", () => {
		const { container } = render(
			<SuggestedQuestions questions={[]} onSelect={vi.fn()} />,
		);

		expect(container).toBeEmptyDOMElement();
	});
});

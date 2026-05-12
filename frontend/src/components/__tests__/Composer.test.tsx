import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Composer } from "@/components/Composer";

describe("Composer", () => {
	it("submits the trimmed message on Cmd+Enter", async () => {
		const user = userEvent.setup();
		const onSend = vi.fn();
		render(<Composer onSend={onSend} />);

		const textarea = screen.getByRole("textbox", { name: /message/i });
		await user.type(textarea, "what was the revenue in 2009?");
		await user.keyboard("{Meta>}{Enter}{/Meta}");

		expect(onSend).toHaveBeenCalledExactlyOnceWith(
			"what was the revenue in 2009?",
		);
	});

	it("does not submit on plain Enter (newline behavior preserved)", async () => {
		const user = userEvent.setup();
		const onSend = vi.fn();
		render(<Composer onSend={onSend} />);

		const textarea = screen.getByRole("textbox", { name: /message/i });
		await user.type(textarea, "line one");
		await user.keyboard("{Enter}");
		await user.type(textarea, "line two");

		expect(onSend).not.toHaveBeenCalled();
		expect(textarea).toHaveValue("line one\nline two");
	});

	it("shows the 'Pin a document first' hint when disabled", () => {
		render(<Composer onSend={vi.fn()} disabled />);

		expect(screen.getByText("Pin a document first")).toBeVisible();
		expect(screen.getByRole("textbox", { name: /message/i })).toBeDisabled();
	});

	it("renders the character counter when the value exceeds 28k chars", async () => {
		const user = userEvent.setup();
		render(<Composer onSend={vi.fn()} />);
		const textarea = screen.getByRole("textbox", { name: /message/i });

		expect(screen.queryByText(/\/ 32,000$/)).not.toBeInTheDocument();

		await user.click(textarea);
		await user.paste("a".repeat(28_001));

		expect(screen.getByText("28,001 / 32,000")).toBeInTheDocument();
	});
});

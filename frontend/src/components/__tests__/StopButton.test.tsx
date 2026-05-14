import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StopButton } from "@/components/StopButton";

describe("StopButton", () => {
	it.each([
		["ready" as const],
		["error" as const],
	])("does not render when status is %s", (status) => {
		render(
			<StopButton
				status={status}
				stop={vi.fn()}
				streamingMessageId="m1"
				onStopped={vi.fn()}
			/>,
		);

		expect(
			screen.queryByRole("button", { name: /stop generating/i }),
		).not.toBeInTheDocument();
	});

	it.each([
		["streaming" as const],
		["submitted" as const],
	])("renders while status is %s", (status) => {
		render(
			<StopButton
				status={status}
				stop={vi.fn()}
				streamingMessageId="m1"
				onStopped={vi.fn()}
			/>,
		);

		expect(
			screen.getByRole("button", { name: /stop generating/i }),
		).toBeVisible();
	});

	it("invokes stop() and records the streaming message id on click", async () => {
		const user = userEvent.setup();
		const stop = vi.fn();
		const onStopped = vi.fn();

		render(
			<StopButton
				status="streaming"
				stop={stop}
				streamingMessageId="msg-123"
				onStopped={onStopped}
			/>,
		);

		await user.click(screen.getByRole("button", { name: /stop generating/i }));

		expect(stop).toHaveBeenCalledOnce();
		expect(onStopped).toHaveBeenCalledExactlyOnceWith("msg-123");
	});

	it("calls stop() but skips onStopped before any assistant chunk arrives", async () => {
		const user = userEvent.setup();
		const stop = vi.fn();
		const onStopped = vi.fn();

		render(
			<StopButton
				status="submitted"
				stop={stop}
				streamingMessageId={null}
				onStopped={onStopped}
			/>,
		);

		await user.click(screen.getByRole("button", { name: /stop generating/i }));

		expect(stop).toHaveBeenCalledOnce();
		expect(onStopped).not.toHaveBeenCalled();
	});
});

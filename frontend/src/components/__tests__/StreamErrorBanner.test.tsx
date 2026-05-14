import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StreamErrorBanner } from "@/components/StreamErrorBanner";

function makeConcurrentError(): Error {
	return new Error(
		JSON.stringify({
			type: "about:blank/conversation-busy",
			title: "Conversation busy",
			status: 409,
			detail: "Another request is already in flight.",
		}),
	);
}

function makeServerError(): Error {
	return new Error(JSON.stringify({ status: 500, title: "boom" }));
}

describe("StreamErrorBanner", () => {
	it("renders nothing when there is no error", () => {
		const { container } = render(
			<StreamErrorBanner
				error={undefined}
				onRetry={vi.fn()}
				onDismiss={vi.fn()}
			/>,
		);
		expect(container.firstChild).toBeNull();
	});

	it("shows the concurrent-conversation copy for a 409 error", () => {
		render(
			<StreamErrorBanner
				error={makeConcurrentError()}
				onRetry={vi.fn()}
				onDismiss={vi.fn()}
			/>,
		);
		expect(screen.getByText(/another response is in progress/i)).toBeVisible();
		expect(screen.getByTestId("stream-error-banner")).toHaveAttribute(
			"data-error-class",
			"concurrent",
		);
	});

	it("shows the server-error copy for a 5xx error", () => {
		render(
			<StreamErrorBanner
				error={makeServerError()}
				onRetry={vi.fn()}
				onDismiss={vi.fn()}
			/>,
		);
		expect(screen.getByText(/server error/i)).toBeVisible();
		expect(screen.getByTestId("stream-error-banner")).toHaveAttribute(
			"data-error-class",
			"server",
		);
	});

	it("shows the network copy for a fetch failure", () => {
		render(
			<StreamErrorBanner
				error={new TypeError("Failed to fetch")}
				onRetry={vi.fn()}
				onDismiss={vi.fn()}
			/>,
		);
		expect(screen.getByText(/connection lost/i)).toBeVisible();
	});

	it("shows generic copy for an unrecognised error", () => {
		render(
			<StreamErrorBanner
				error={new Error("provider exploded")}
				onRetry={vi.fn()}
				onDismiss={vi.fn()}
			/>,
		);
		expect(screen.getByText(/something went wrong/i)).toBeVisible();
	});

	it("invokes onRetry when Retry is clicked", async () => {
		const user = userEvent.setup();
		const onRetry = vi.fn();
		render(
			<StreamErrorBanner
				error={makeServerError()}
				onRetry={onRetry}
				onDismiss={vi.fn()}
			/>,
		);
		await user.click(screen.getByRole("button", { name: /retry/i }));
		expect(onRetry).toHaveBeenCalledOnce();
	});

	it("invokes onDismiss when the close button is clicked", async () => {
		const user = userEvent.setup();
		const onDismiss = vi.fn();
		render(
			<StreamErrorBanner
				error={makeServerError()}
				onRetry={vi.fn()}
				onDismiss={onDismiss}
			/>,
		);
		await user.click(screen.getByRole("button", { name: /dismiss error/i }));
		expect(onDismiss).toHaveBeenCalledOnce();
	});

	it("disables the retry button while a retry is in flight", () => {
		render(
			<StreamErrorBanner
				error={makeServerError()}
				onRetry={vi.fn()}
				onDismiss={vi.fn()}
				isRetrying
			/>,
		);
		const retry = screen.getByRole("button", { name: /retrying/i });
		expect(retry).toBeDisabled();
	});
});

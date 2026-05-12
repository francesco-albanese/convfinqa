import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmptyState } from "@/components/EmptyState";

describe("EmptyState", () => {
	it("renders the mockup C empty-state heading and supporting copy", () => {
		render(<EmptyState />);

		expect(screen.getByText(/no document pinned/i)).toBeVisible();
		expect(
			screen.getByRole("heading", {
				name: /pin a document to start chatting/i,
			}),
		).toBeVisible();
		expect(
			screen.getByText(/conversations in convfinqa are per document/i),
		).toBeVisible();
	});

	it("calls onPinDocument when the CTA is provided and clicked", async () => {
		const user = userEvent.setup();
		const onPinDocument = vi.fn();
		render(<EmptyState onPinDocument={onPinDocument} />);

		await user.click(screen.getByRole("button", { name: /pin a document/i }));

		expect(onPinDocument).toHaveBeenCalledTimes(1);
	});

	it("hides the CTA when no handler is supplied", () => {
		render(<EmptyState />);

		expect(
			screen.queryByRole("button", { name: /pin a document/i }),
		).not.toBeInTheDocument();
	});
});

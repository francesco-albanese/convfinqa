import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { describe, expect, it } from "vitest";
import { useModalDialog } from "@/lib/ui/useModalDialog";

type HarnessProps = {
	initialFocusViaDataAttr?: boolean;
};

function Harness({ initialFocusViaDataAttr = false }: HarnessProps) {
	const [open, setOpen] = useState(false);
	const containerRef = useRef<HTMLElement>(null);

	useModalDialog({
		open,
		containerRef,
		onClose: () => setOpen(false),
	});

	return (
		<div>
			<button type="button" data-testid="opener" onClick={() => setOpen(true)}>
				Open dialog
			</button>
			<button type="button" data-testid="outside-after">
				Outside button after opener
			</button>
			{open ? (
				<aside
					ref={containerRef}
					data-testid="dialog"
					tabIndex={-1}
					aria-label="Test dialog"
				>
					<button
						type="button"
						data-testid="dialog-first"
						data-modal-initial-focus={initialFocusViaDataAttr ? "" : undefined}
					>
						First
					</button>
					<button type="button" data-testid="dialog-second">
						Second
					</button>
					<button type="button" data-testid="dialog-last">
						Last
					</button>
				</aside>
			) : null}
		</div>
	);
}

describe("useModalDialog", () => {
	it("moves initial focus to the first focusable when no explicit target is set", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.click(screen.getByTestId("opener"));

		expect(screen.getByTestId("dialog-first")).toHaveFocus();
	});

	it("honours data-modal-initial-focus when present", async () => {
		const user = userEvent.setup();
		render(<Harness initialFocusViaDataAttr />);

		await user.click(screen.getByTestId("opener"));

		expect(screen.getByTestId("dialog-first")).toHaveFocus();
	});

	it("closes when Escape is pressed inside the container", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.click(screen.getByTestId("opener"));
		expect(screen.getByTestId("dialog")).toBeInTheDocument();

		await user.keyboard("{Escape}");

		expect(screen.queryByTestId("dialog")).not.toBeInTheDocument();
	});

	it("returns focus to the trigger element when the dialog closes", async () => {
		const user = userEvent.setup();
		render(<Harness />);
		const opener = screen.getByTestId("opener");

		await user.click(opener);
		await user.keyboard("{Escape}");

		expect(opener).toHaveFocus();
	});

	it("wraps Tab focus from the last focusable back to the first", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.click(screen.getByTestId("opener"));
		screen.getByTestId("dialog-last").focus();

		await user.tab();

		expect(screen.getByTestId("dialog-first")).toHaveFocus();
	});

	it("wraps Shift+Tab from the first focusable to the last", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.click(screen.getByTestId("opener"));
		screen.getByTestId("dialog-first").focus();

		await user.tab({ shift: true });

		expect(screen.getByTestId("dialog-last")).toHaveFocus();
	});
});

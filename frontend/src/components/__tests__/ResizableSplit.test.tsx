import { fireEvent, render, screen } from "@testing-library/react";
import { afterAll, beforeEach, describe, expect, it } from "vitest";
import { ResizableSplit } from "@/components/ResizableSplit";
import {
	PANEL_WIDTH_DEFAULT,
	PANEL_WIDTH_MIN,
	panelWidthStore,
	resetPanelWidth,
} from "@/lib/ui/panelWidthStore";

const ORIGINAL_INNER_WIDTH = window.innerWidth;

function setViewportWidth(width: number): void {
	Object.defineProperty(window, "innerWidth", {
		configurable: true,
		writable: true,
		value: width,
	});
}

function getPanelWidthPx(): number {
	const panel = screen.getByTestId("resizable-split");
	return Number.parseFloat(panel.style.width);
}

describe("ResizableSplit", () => {
	beforeEach(() => {
		window.localStorage.clear();
		resetPanelWidth();
		setViewportWidth(1024);
		document.body.style.removeProperty("cursor");
		document.body.style.removeProperty("user-select");
	});

	afterAll(() => {
		setViewportWidth(ORIGINAL_INNER_WIDTH);
	});

	it("renders children with the persisted panel width", () => {
		render(
			<ResizableSplit>
				<div>panel content</div>
			</ResizableSplit>,
		);
		expect(screen.getByText("panel content")).toBeInTheDocument();
		expect(getPanelWidthPx()).toBe(PANEL_WIDTH_DEFAULT);
	});

	it("drags the handle to a new width within bounds via pointer events", () => {
		render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		const handle = screen.getByTestId("resize-handle");

		fireEvent.pointerDown(handle, { clientX: 544 });
		fireEvent.pointerMove(window, { clientX: 624 });
		fireEvent.pointerUp(window, { clientX: 624 });

		// Drag from x=544 (matches the default 480 from the right edge at 1024) to x=624.
		// New width = viewport (1024) - clientX (624) = 400.
		expect(panelWidthStore.state.width).toBe(400);
		expect(getPanelWidthPx()).toBe(400);
	});

	it("clamps the drag to the minimum panel width", () => {
		render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		const handle = screen.getByTestId("resize-handle");

		fireEvent.pointerDown(handle, { clientX: 544 });
		fireEvent.pointerMove(window, { clientX: 1500 });
		fireEvent.pointerUp(window, { clientX: 1500 });

		expect(panelWidthStore.state.width).toBe(PANEL_WIDTH_MIN);
	});

	it("clamps the drag to 60% of the viewport on the upper bound", () => {
		setViewportWidth(1000);
		render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		const handle = screen.getByTestId("resize-handle");

		fireEvent.pointerDown(handle, { clientX: 520 });
		fireEvent.pointerMove(window, { clientX: 0 });
		fireEvent.pointerUp(window, { clientX: 0 });

		expect(panelWidthStore.state.width).toBe(600);
	});

	it("does not move the panel once pointerup fires", () => {
		render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		const handle = screen.getByTestId("resize-handle");

		fireEvent.pointerDown(handle, { clientX: 544 });
		fireEvent.pointerMove(window, { clientX: 624 });
		fireEvent.pointerUp(window, { clientX: 624 });

		const stoppedAt = panelWidthStore.state.width;
		fireEvent.pointerMove(window, { clientX: 100 });
		expect(panelWidthStore.state.width).toBe(stoppedAt);
	});

	it("resizes via arrow keys, jumps to bounds with Home/End", () => {
		render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		const handle = screen.getByTestId("resize-handle");
		handle.focus();

		fireEvent.keyDown(handle, { key: "ArrowRight" });
		expect(panelWidthStore.state.width).toBe(PANEL_WIDTH_DEFAULT - 8);

		fireEvent.keyDown(handle, { key: "ArrowLeft", shiftKey: true });
		expect(panelWidthStore.state.width).toBe(PANEL_WIDTH_DEFAULT - 8 + 32);

		fireEvent.keyDown(handle, { key: "Home" });
		expect(panelWidthStore.state.width).toBe(PANEL_WIDTH_MIN);

		fireEvent.keyDown(handle, { key: "End" });
		expect(panelWidthStore.state.width).toBe(1024 * 0.6);
	});

	it("double-clicking the handle resets the width to the default", () => {
		render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		const handle = screen.getByTestId("resize-handle");

		fireEvent.pointerDown(handle, { clientX: 544 });
		fireEvent.pointerMove(window, { clientX: 700 });
		fireEvent.pointerUp(window, { clientX: 700 });
		expect(panelWidthStore.state.width).not.toBe(PANEL_WIDTH_DEFAULT);

		fireEvent.doubleClick(handle);
		expect(panelWidthStore.state.width).toBe(PANEL_WIDTH_DEFAULT);
		expect(getPanelWidthPx()).toBe(PANEL_WIDTH_DEFAULT);
	});

	it("restores body cursor/user-select after a pointercancel mid-drag", () => {
		render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		const handle = screen.getByTestId("resize-handle");

		fireEvent.pointerDown(handle, { clientX: 544 });
		expect(document.body.style.cursor).toBe("col-resize");
		expect(document.body.style.userSelect).toBe("none");

		fireEvent.pointerCancel(window, { clientX: 544 });
		expect(document.body.style.cursor).toBe("");
		expect(document.body.style.userSelect).toBe("");
	});

	it("cleans up body cursor/user-select if it unmounts while dragging", () => {
		const { unmount } = render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		const handle = screen.getByTestId("resize-handle");

		fireEvent.pointerDown(handle, { clientX: 544 });
		expect(document.body.style.cursor).toBe("col-resize");

		unmount();
		expect(document.body.style.cursor).toBe("");
		expect(document.body.style.userSelect).toBe("");
	});

	it("hydrates the width from the persisted store value on mount", () => {
		panelWidthStore.setState((state) => ({ ...state, width: 612 }));

		const { unmount } = render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		unmount();

		render(
			<ResizableSplit>
				<div>panel</div>
			</ResizableSplit>,
		);
		expect(getPanelWidthPx()).toBe(612);
	});
});

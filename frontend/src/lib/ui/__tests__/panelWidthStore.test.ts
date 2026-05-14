import { beforeEach, describe, expect, it } from "vitest";
import {
	clampPanelWidth,
	createPanelWidthStore,
	PANEL_WIDTH_DEFAULT,
	PANEL_WIDTH_MIN,
	PANEL_WIDTH_STORAGE_KEY,
} from "@/lib/ui/panelWidthStore";

describe("panelWidthStore", () => {
	beforeEach(() => {
		window.localStorage.clear();
	});

	it("defaults to PANEL_WIDTH_DEFAULT when storage is empty", () => {
		const store = createPanelWidthStore();
		expect(store.state.width).toBe(PANEL_WIDTH_DEFAULT);
	});

	it("persists changes so a fresh instance reads the previous value", () => {
		const first = createPanelWidthStore();
		first.setState((state) => ({ ...state, width: 612 }));

		const second = createPanelWidthStore();
		expect(second.state.width).toBe(612);
	});

	it("recovers from corrupt JSON in storage by returning the default width", () => {
		window.localStorage.setItem(PANEL_WIDTH_STORAGE_KEY, "{not json");
		const store = createPanelWidthStore();
		expect(store.state.width).toBe(PANEL_WIDTH_DEFAULT);
	});

	it("ignores stored payloads with the wrong shape", () => {
		window.localStorage.setItem(
			PANEL_WIDTH_STORAGE_KEY,
			JSON.stringify({ width: "480" }),
		);
		const store = createPanelWidthStore();
		expect(store.state.width).toBe(PANEL_WIDTH_DEFAULT);
	});

	it("clamps a persisted value below the minimum back up to the minimum on read", () => {
		window.localStorage.setItem(
			PANEL_WIDTH_STORAGE_KEY,
			JSON.stringify({ width: 100 }),
		);
		const store = createPanelWidthStore();
		expect(store.state.width).toBe(PANEL_WIDTH_MIN);
	});
});

describe("clampPanelWidth", () => {
	it("clamps below-minimum to the minimum", () => {
		expect(clampPanelWidth(100, 1024)).toBe(PANEL_WIDTH_MIN);
	});

	it("clamps above-60%-of-viewport to 60% of viewport", () => {
		expect(clampPanelWidth(900, 1000)).toBe(600);
	});

	it("returns the input when it sits inside the bounds", () => {
		expect(clampPanelWidth(420, 1200)).toBe(420);
	});

	it("falls back to the default for non-finite values", () => {
		expect(clampPanelWidth(Number.NaN, 1024)).toBe(PANEL_WIDTH_DEFAULT);
	});
});

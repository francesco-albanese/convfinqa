import { beforeEach, describe, expect, it } from "vitest";
import { createSidebarStore, SIDEBAR_STORAGE_KEY } from "@/lib/ui/sidebarStore";

describe("sidebarStore", () => {
	beforeEach(() => {
		window.localStorage.clear();
	});

	it("defaults to expanded (collapsed=false) when storage is empty", () => {
		const store = createSidebarStore();
		expect(store.state.collapsed).toBe(false);
	});

	it("toggle flips collapsed state", () => {
		const store = createSidebarStore();
		store.setState((state) => ({ ...state, collapsed: !state.collapsed }));
		expect(store.state.collapsed).toBe(true);
		store.setState((state) => ({ ...state, collapsed: !state.collapsed }));
		expect(store.state.collapsed).toBe(false);
	});

	it("persists changes so a fresh instance reads the previous value", () => {
		const first = createSidebarStore();
		first.setState((state) => ({ ...state, collapsed: true }));

		const second = createSidebarStore();
		expect(second.state.collapsed).toBe(true);
	});

	it("recovers from corrupt JSON in storage by returning defaults", () => {
		window.localStorage.setItem(SIDEBAR_STORAGE_KEY, "{not json");
		const store = createSidebarStore();
		expect(store.state.collapsed).toBe(false);
	});

	it("ignores stored payloads with the wrong shape", () => {
		window.localStorage.setItem(
			SIDEBAR_STORAGE_KEY,
			JSON.stringify({ collapsed: "yes" }),
		);
		const store = createSidebarStore();
		expect(store.state.collapsed).toBe(false);
	});
});

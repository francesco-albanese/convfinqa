import { beforeEach, describe, expect, it } from "vitest";
import { createModelStore, MODEL_STORAGE_KEY } from "@/lib/ui/modelStore";

describe("modelStore", () => {
	beforeEach(() => {
		window.localStorage.clear();
	});

	it("defaults to no selection when storage is empty", () => {
		const store = createModelStore();
		expect(store.state.selected).toBeNull();
	});

	it("persists the selected model so a fresh instance reads it back", () => {
		const first = createModelStore();
		first.setState((state) => ({
			...state,
			selected: "gemini/gemini-2.5-flash",
		}));

		const second = createModelStore();
		expect(second.state.selected).toBe("gemini/gemini-2.5-flash");
	});

	it("recovers from corrupt JSON in storage by returning defaults", () => {
		window.localStorage.setItem(MODEL_STORAGE_KEY, "{not json");
		const store = createModelStore();
		expect(store.state.selected).toBeNull();
	});

	it("ignores stored payloads with the wrong shape", () => {
		window.localStorage.setItem(
			MODEL_STORAGE_KEY,
			JSON.stringify({ selected: 42 }),
		);
		const store = createModelStore();
		expect(store.state.selected).toBeNull();
	});
});

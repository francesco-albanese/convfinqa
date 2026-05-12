import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

function createMemoryStorage(): Storage {
	const store = new Map<string, string>();
	return {
		get length() {
			return store.size;
		},
		clear: () => store.clear(),
		getItem: (key: string) =>
			store.has(key) ? (store.get(key) as string) : null,
		setItem: (key: string, value: string) => {
			store.set(key, String(value));
		},
		removeItem: (key: string) => {
			store.delete(key);
		},
		key: (index: number) => Array.from(store.keys())[index] ?? null,
	};
}

Object.defineProperty(window, "localStorage", {
	configurable: true,
	value: createMemoryStorage(),
});
Object.defineProperty(window, "sessionStorage", {
	configurable: true,
	value: createMemoryStorage(),
});

afterEach(() => {
	cleanup();
	window.localStorage.clear();
	window.sessionStorage.clear();
});

window.scrollTo = () => {};

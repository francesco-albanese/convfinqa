import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import {
	collapsedGroupsStorageKey,
	readCollapsedGroups,
	useCollapsedGroups,
	writeCollapsedGroups,
} from "@/lib/ui/collapsedGroupsStore";

const USER_A = "dev-user-aaa";
const USER_B = "dev-user-bbb";

describe("collapsedGroupsStore", () => {
	beforeEach(() => {
		window.localStorage.clear();
	});

	it("returns an empty set when storage is empty", () => {
		expect(readCollapsedGroups(USER_A)).toEqual(new Set());
	});

	it("persists collapsed group ids and reads them back for the same user", () => {
		writeCollapsedGroups(USER_A, new Set(["doc-1", "doc-2"]));
		expect(readCollapsedGroups(USER_A)).toEqual(new Set(["doc-1", "doc-2"]));
	});

	it("isolates state between users", () => {
		writeCollapsedGroups(USER_A, new Set(["doc-1"]));
		writeCollapsedGroups(USER_B, new Set(["doc-9"]));
		expect(readCollapsedGroups(USER_A)).toEqual(new Set(["doc-1"]));
		expect(readCollapsedGroups(USER_B)).toEqual(new Set(["doc-9"]));
	});

	it("recovers from corrupt JSON in storage", () => {
		window.localStorage.setItem(collapsedGroupsStorageKey(USER_A), "{not json");
		expect(readCollapsedGroups(USER_A)).toEqual(new Set());
	});

	it("ignores stored payloads with the wrong shape", () => {
		window.localStorage.setItem(
			collapsedGroupsStorageKey(USER_A),
			JSON.stringify({ collapsed: ["doc-1"] }),
		);
		expect(readCollapsedGroups(USER_A)).toEqual(new Set());
	});

	it("ignores arrays whose items are not all strings", () => {
		window.localStorage.setItem(
			collapsedGroupsStorageKey(USER_A),
			JSON.stringify(["doc-1", 42]),
		);
		expect(readCollapsedGroups(USER_A)).toEqual(new Set());
	});
});

describe("useCollapsedGroups", () => {
	beforeEach(() => {
		window.localStorage.clear();
	});

	it("toggling a group adds it on first call and removes it on the second", () => {
		const { result } = renderHook(() => useCollapsedGroups(USER_A));

		expect(result.current.collapsedGroups.has("doc-1")).toBe(false);

		act(() => {
			result.current.toggleGroup("doc-1");
		});
		expect(result.current.collapsedGroups.has("doc-1")).toBe(true);

		act(() => {
			result.current.toggleGroup("doc-1");
		});
		expect(result.current.collapsedGroups.has("doc-1")).toBe(false);
	});

	it("a remounted hook reads the previously persisted state", () => {
		const first = renderHook(() => useCollapsedGroups(USER_A));
		act(() => {
			first.result.current.toggleGroup("doc-1");
		});
		first.unmount();

		const second = renderHook(() => useCollapsedGroups(USER_A));
		expect(second.result.current.collapsedGroups.has("doc-1")).toBe(true);
	});

	it("switching userId reloads state for the new user", () => {
		writeCollapsedGroups(USER_A, new Set(["doc-1"]));
		writeCollapsedGroups(USER_B, new Set(["doc-9"]));

		const { result, rerender } = renderHook(
			({ userId }: { userId: string }) => useCollapsedGroups(userId),
			{ initialProps: { userId: USER_A } },
		);
		expect(result.current.collapsedGroups).toEqual(new Set(["doc-1"]));

		rerender({ userId: USER_B });
		expect(result.current.collapsedGroups).toEqual(new Set(["doc-9"]));
	});
});

import { useCallback, useEffect, useState } from "react";

export const COLLAPSED_GROUPS_STORAGE_PREFIX =
	"convfinqa:sidebar:collapsedGroups";

export function collapsedGroupsStorageKey(userId: string): string {
	return `${COLLAPSED_GROUPS_STORAGE_PREFIX}:${userId}`;
}

export function readCollapsedGroups(userId: string): Set<string> {
	try {
		const raw = window.localStorage.getItem(collapsedGroupsStorageKey(userId));
		if (raw === null) return new Set();
		const parsed: unknown = JSON.parse(raw);
		if (Array.isArray(parsed) && parsed.every((v) => typeof v === "string")) {
			return new Set(parsed);
		}
	} catch {
		// Corrupt JSON or storage blocked — fall through to defaults.
	}
	return new Set();
}

export function writeCollapsedGroups(userId: string, ids: Set<string>): void {
	try {
		window.localStorage.setItem(
			collapsedGroupsStorageKey(userId),
			JSON.stringify(Array.from(ids)),
		);
	} catch {
		// Quota exceeded or storage blocked — silently drop the write.
	}
}

export type UseCollapsedGroups = {
	collapsedGroups: Set<string>;
	toggleGroup: (documentId: string) => void;
};

export function useCollapsedGroups(userId: string): UseCollapsedGroups {
	const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(() =>
		readCollapsedGroups(userId),
	);

	useEffect(() => {
		setCollapsedGroups(readCollapsedGroups(userId));
	}, [userId]);

	const toggleGroup = useCallback(
		(documentId: string) => {
			setCollapsedGroups((current) => {
				const next = new Set(current);
				if (next.has(documentId)) {
					next.delete(documentId);
				} else {
					next.add(documentId);
				}
				writeCollapsedGroups(userId, next);
				return next;
			});
		},
		[userId],
	);

	return { collapsedGroups, toggleGroup };
}

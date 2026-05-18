import type { ChatDocumentGroup } from "@/lib/transforms/groupByDocument";

export type FlattenedRow =
	| { kind: "header"; group: ChatDocumentGroup; isCollapsed: boolean }
	| {
			kind: "chat";
			groupId: string;
			chat: ChatDocumentGroup["conversations"][number];
	  };

export function documentLabel(document: ChatDocumentGroup["document"]): string {
	if (document.ticker && document.year !== null) {
		return `${document.ticker} · ${document.year}`;
	}
	return document.title ?? document.ticker ?? document.id;
}

export function formatTimestamp(iso: string): string {
	const parsed = new Date(iso);
	if (Number.isNaN(parsed.getTime())) {
		return "";
	}
	return parsed.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
	});
}

function documentMatches(
	document: ChatDocumentGroup["document"],
	needle: string,
): boolean {
	const title = document.title?.toLowerCase() ?? "";
	const ticker = document.ticker?.toLowerCase() ?? "";
	return title.includes(needle) || ticker.includes(needle);
}

export function filterGroups(
	groups: ChatDocumentGroup[],
	query: string,
): ChatDocumentGroup[] {
	const needle = query.trim().toLowerCase();
	if (needle.length === 0) {
		return groups;
	}
	const filtered: ChatDocumentGroup[] = [];
	for (const group of groups) {
		if (documentMatches(group.document, needle)) {
			filtered.push(group);
			continue;
		}
		const conversations = group.conversations.filter((conversation) =>
			conversation.last_message_preview.toLowerCase().includes(needle),
		);
		if (conversations.length > 0) {
			filtered.push({ document: group.document, conversations });
		}
	}
	return filtered;
}

export function flattenRows(
	groups: ChatDocumentGroup[],
	collapsedGroups: Set<string>,
): FlattenedRow[] {
	const rows: FlattenedRow[] = [];
	for (const group of groups) {
		const isCollapsed = collapsedGroups.has(group.document.id);
		rows.push({ kind: "header", group, isCollapsed });
		if (!isCollapsed) {
			for (const chat of group.conversations) {
				rows.push({ kind: "chat", groupId: group.document.id, chat });
			}
		}
	}
	return rows;
}

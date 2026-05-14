import type { ChatDocument, ChatSummary } from "@/lib/queries/chats";

export type ChatDocumentGroup = {
	document: ChatDocument;
	conversations: ChatSummary[];
};

function titleSortKey(document: ChatDocument): string {
	return document.title ?? "";
}

export function groupByDocument(items: ChatSummary[]): ChatDocumentGroup[] {
	const byDocument = new Map<string, ChatDocumentGroup>();

	for (const item of items) {
		const existing = byDocument.get(item.document.id);
		if (existing) {
			existing.conversations.push(item);
		} else {
			byDocument.set(item.document.id, {
				document: item.document,
				conversations: [item],
			});
		}
	}

	const groups = Array.from(byDocument.values());

	for (const group of groups) {
		group.conversations.sort((a, b) =>
			a.last_message_at < b.last_message_at ? 1 : -1,
		);
	}

	groups.sort((a, b) => {
		const titleA = titleSortKey(a.document);
		const titleB = titleSortKey(b.document);
		if (titleA === titleB) {
			return a.document.id < b.document.id ? -1 : 1;
		}
		return titleA < titleB ? -1 : 1;
	});

	return groups;
}

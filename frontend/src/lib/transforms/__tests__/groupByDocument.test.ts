import { describe, expect, it } from "vitest";
import type { ChatSummary } from "@/lib/queries/chats";
import { groupByDocument } from "@/lib/transforms/groupByDocument";

function summary(
	overrides: Partial<ChatSummary> & { id: string },
): ChatSummary {
	return {
		id: overrides.id,
		document: overrides.document ?? {
			id: "doc-aaa",
			ticker: "AAA",
			year: 2024,
			title: "AAA 2024",
		},
		last_message_preview: overrides.last_message_preview ?? "preview",
		last_message_at: overrides.last_message_at ?? "2026-05-14T10:00:00+00:00",
		title: overrides.title ?? null,
	};
}

describe("groupByDocument", () => {
	it("groups conversations by document and sorts groups by newest child conversation", () => {
		const items: ChatSummary[] = [
			summary({
				id: "c-beta-1",
				document: { id: "doc-beta", ticker: "BB", year: 2025, title: "Beta" },
				last_message_at: "2026-05-14T09:00:00+00:00",
			}),
			summary({
				id: "c-alpha-1",
				document: { id: "doc-alpha", ticker: "AA", year: 2024, title: "Alpha" },
				last_message_at: "2026-05-15T09:00:00+00:00",
			}),
		];

		const groups = groupByDocument(items);

		expect(groups.map((g) => g.document.id)).toEqual(["doc-alpha", "doc-beta"]);
		expect(groups.map((g) => g.conversations.length)).toEqual([1, 1]);
	});

	it("sorts conversations within a group by last_message_at descending", () => {
		const docA = {
			id: "doc-aaa",
			ticker: "AA",
			year: 2024,
			title: "AAA",
		};
		const items: ChatSummary[] = [
			summary({
				id: "older",
				document: docA,
				last_message_at: "2026-05-10T09:00:00+00:00",
			}),
			summary({
				id: "newest",
				document: docA,
				last_message_at: "2026-05-14T09:00:00+00:00",
			}),
			summary({
				id: "middle",
				document: docA,
				last_message_at: "2026-05-12T09:00:00+00:00",
			}),
		];

		const [group] = groupByDocument(items);

		expect(group?.conversations.map((c) => c.id)).toEqual([
			"newest",
			"middle",
			"older",
		]);
	});

	it("breaks newest timestamp ties deterministically using document.id", () => {
		const items: ChatSummary[] = [
			summary({
				id: "c-z",
				document: { id: "doc-z", ticker: "Z", year: 2024, title: "FY 2024" },
			}),
			summary({
				id: "c-a",
				document: { id: "doc-a", ticker: "A", year: 2024, title: "FY 2024" },
			}),
		];

		const groups = groupByDocument(items);

		expect(groups.map((g) => g.document.id)).toEqual(["doc-a", "doc-z"]);
	});

	it("handles null titles without crashing", () => {
		const items: ChatSummary[] = [
			summary({
				id: "c-named",
				document: { id: "doc-named", ticker: "X", year: 2024, title: "Zeta" },
			}),
			summary({
				id: "c-unnamed",
				document: { id: "doc-unnamed", ticker: null, year: null, title: null },
			}),
		];

		const groups = groupByDocument(items);

		expect(groups.map((g) => g.document.id)).toEqual([
			"doc-named",
			"doc-unnamed",
		]);
	});
});

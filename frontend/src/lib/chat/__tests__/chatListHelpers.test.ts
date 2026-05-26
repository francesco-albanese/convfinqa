import { describe, expect, it } from "vitest";
import type { ChatDocumentGroup } from "@/lib/transforms/groupByDocument";
import {
	documentLabel,
	filterGroups,
	flattenRows,
	formatTimestamp,
} from "../chatListHelpers";

function makeGroup(
	overrides: Partial<ChatDocumentGroup["document"]> & {
		conversations?: ChatDocumentGroup["conversations"];
	},
): ChatDocumentGroup {
	const { conversations = [], ...docOverrides } = overrides;
	return {
		document: {
			id: "doc-1",
			title: null,
			ticker: null,
			year: null,
			...docOverrides,
		},
		conversations,
	};
}

function makeChat(preview: string): ChatDocumentGroup["conversations"][number] {
	return {
		id: crypto.randomUUID(),
		document: {
			id: "doc-1",
			title: null,
			ticker: null,
			year: null,
		},
		last_message_preview: preview,
		last_message_at: "2024-01-15T10:00:00Z",
		title: null,
	};
}

describe("documentLabel", () => {
	it("returns ticker and year when both present", () => {
		const doc = makeGroup({ ticker: "AAPL", year: 2023 }).document;
		expect(documentLabel(doc)).toBe("AAPL · 2023");
	});

	it("falls back to title when ticker or year missing", () => {
		expect(documentLabel(makeGroup({ title: "Annual Report" }).document)).toBe(
			"Annual Report",
		);
	});

	it("falls back to ticker when title null and year null", () => {
		expect(documentLabel(makeGroup({ ticker: "MSFT" }).document)).toBe("MSFT");
	});

	it("falls back to id as last resort", () => {
		expect(documentLabel(makeGroup({ id: "doc-42" }).document)).toBe("doc-42");
	});
});

describe("formatTimestamp", () => {
	it("returns empty string for invalid date", () => {
		expect(formatTimestamp("not-a-date")).toBe("");
	});

	it("returns a non-empty string for a valid ISO date", () => {
		const result = formatTimestamp("2024-06-15T12:00:00Z");
		expect(result.length).toBeGreaterThan(0);
	});
});

describe("filterGroups", () => {
	const alpha = makeGroup({
		id: "alpha",
		ticker: "AAPL",
		conversations: [makeChat("revenue growth discussion")],
	});
	const beta = makeGroup({
		id: "beta",
		title: "Beta Corp",
		conversations: [makeChat("profit margins analysis")],
	});

	it("returns all groups when query is empty", () => {
		expect(filterGroups([alpha, beta], "")).toHaveLength(2);
		expect(filterGroups([alpha, beta], "   ")).toHaveLength(2);
	});

	it("includes a group when ticker matches", () => {
		const result = filterGroups([alpha, beta], "aapl");
		expect(result).toHaveLength(1);
		expect(result[0]?.document.id).toBe("alpha");
	});

	it("includes a group when title matches", () => {
		const result = filterGroups([alpha, beta], "beta");
		expect(result).toHaveLength(1);
		expect(result[0]?.document.id).toBe("beta");
	});

	it("filters conversations by preview when document does not match", () => {
		const group = makeGroup({
			id: "gamma",
			title: "Gamma Inc",
			conversations: [
				makeChat("dividends payout"),
				makeChat("cash flow forecast"),
			],
		});
		const result = filterGroups([group], "dividends");
		expect(result).toHaveLength(1);
		expect(result[0]?.conversations).toHaveLength(1);
		expect(result[0]?.conversations[0]?.last_message_preview).toBe(
			"dividends payout",
		);
	});

	it("excludes group when neither document nor conversations match", () => {
		expect(filterGroups([alpha, beta], "xyz123")).toHaveLength(0);
	});
});

describe("flattenRows", () => {
	const chat1 = makeChat("first");
	const chat2 = makeChat("second");
	const group = makeGroup({ id: "g1", conversations: [chat1, chat2] });

	it("emits a header then chat rows for an expanded group", () => {
		const rows = flattenRows([group], new Set());
		expect(rows).toHaveLength(3);
		expect(rows[0]).toMatchObject({ kind: "header", isCollapsed: false });
		expect(rows[1]).toMatchObject({ kind: "chat" });
		expect(rows[2]).toMatchObject({ kind: "chat" });
	});

	it("emits only the header for a collapsed group", () => {
		const rows = flattenRows([group], new Set(["g1"]));
		expect(rows).toHaveLength(1);
		expect(rows[0]).toMatchObject({ kind: "header", isCollapsed: true });
	});

	it("handles multiple groups with mixed collapse state", () => {
		const group2 = makeGroup({ id: "g2", conversations: [makeChat("msg")] });
		const rows = flattenRows([group, group2], new Set(["g1"]));
		expect(rows).toHaveLength(3);
		expect(rows[0]).toMatchObject({ kind: "header", isCollapsed: true });
		expect(rows[1]).toMatchObject({ kind: "header", isCollapsed: false });
		expect(rows[2]).toMatchObject({ kind: "chat" });
	});
});

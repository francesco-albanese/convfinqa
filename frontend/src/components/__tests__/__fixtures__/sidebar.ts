import { vi } from "vitest";
import type { ChatList } from "@/lib/queries/chats";

export const TEST_USER_ID = "dev-user-sidebar-test";

export const ME_RESPONSE = { user_id: TEST_USER_ID, email: null };

export function jsonResponse(body: unknown): Response {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

export function makeSummary(opts: {
	id: string;
	docId: string;
	ticker: string;
	year: number;
	title: string;
	preview: string;
	at: string;
	convTitle?: string | null;
}) {
	return {
		id: opts.id,
		document: {
			id: opts.docId,
			ticker: opts.ticker,
			year: opts.year,
			title: opts.title,
		},
		last_message_preview: opts.preview,
		last_message_at: opts.at,
		title: opts.convTitle ?? null,
	};
}

export const SAMPLE_LIST: ChatList = {
	items: [
		makeSummary({
			id: "conv-a1",
			docId: "doc-aaa",
			ticker: "AAA",
			year: 2024,
			title: "AAA 2024",
			preview: "Revenue trend for the year",
			at: "2026-05-14T08:00:00+00:00",
		}),
		makeSummary({
			id: "conv-a2",
			docId: "doc-aaa",
			ticker: "AAA",
			year: 2024,
			title: "AAA 2024",
			preview: "Operating margin commentary",
			at: "2026-05-13T08:00:00+00:00",
		}),
		makeSummary({
			id: "conv-b1",
			docId: "doc-bbb",
			ticker: "BBB",
			year: 2023,
			title: "BBB 2023",
			preview: "Debt covenants review",
			at: "2026-05-12T08:00:00+00:00",
		}),
		makeSummary({
			id: "conv-b2",
			docId: "doc-bbb",
			ticker: "BBB",
			year: 2023,
			title: "BBB 2023",
			preview: "Cash flow analysis",
			at: "2026-05-11T08:00:00+00:00",
		}),
		makeSummary({
			id: "conv-c1",
			docId: "doc-ccc",
			ticker: "CCC",
			year: 2025,
			title: "CCC 2025",
			preview: "Net income discussion",
			at: "2026-05-10T08:00:00+00:00",
		}),
		makeSummary({
			id: "conv-c2",
			docId: "doc-ccc",
			ticker: "CCC",
			year: 2025,
			title: "CCC 2025",
			preview: "Capex projections summary",
			at: "2026-05-09T08:00:00+00:00",
		}),
	],
};

export function makeLargeList(count: number): ChatList {
	return {
		items: Array.from({ length: count }, (_, i) =>
			makeSummary({
				id: `conv-${i}`,
				docId: `doc-${i}`,
				ticker: `T${i}`,
				year: 2024,
				title: `Doc ${i}`,
				preview: `Preview ${i}`,
				at: `2026-05-${String((i % 28) + 1).padStart(2, "0")}T08:00:00+00:00`,
			}),
		),
	};
}

export function stubChatListFetch(payload: ChatList): ReturnType<typeof vi.fn> {
	const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
		const url = typeof input === "string" ? input : input.toString();
		if (url.includes("/api/v1/me"))
			return Promise.resolve(jsonResponse(ME_RESPONSE));
		return Promise.resolve(jsonResponse(payload));
	});
	vi.stubGlobal("fetch", fetchMock);
	return fetchMock;
}

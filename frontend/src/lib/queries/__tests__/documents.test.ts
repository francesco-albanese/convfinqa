import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
	buildDocumentsUrl,
	type DocumentListPage,
	useDocumentList,
} from "@/lib/queries/documents";

describe("buildDocumentsUrl", () => {
	it("emits no query string when no filters and no cursor are set", () => {
		expect(buildDocumentsUrl({}, null)).toBe("/v1/documents");
	});

	it("includes q, year_min, year_max when set", () => {
		const url = buildDocumentsUrl(
			{ q: "jkhy", yearMin: 2010, yearMax: 2015 },
			null,
		);
		expect(url).toBe("/v1/documents?q=jkhy&year_min=2010&year_max=2015");
	});

	it("threads the cursor through", () => {
		const url = buildDocumentsUrl({ q: "jkhy" }, "opaque-cursor");
		expect(url).toBe("/v1/documents?q=jkhy&cursor=opaque-cursor");
	});

	it("omits empty/whitespace q so the request stays cache-stable", () => {
		expect(buildDocumentsUrl({ q: "   " }, null)).toBe("/v1/documents");
	});
});

function jsonResponse(body: DocumentListPage): Response {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

function withQueryClient(): {
	wrapper: (props: { children: ReactNode }) => ReactNode;
} {
	const client = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return {
		wrapper: ({ children }) =>
			createElement(QueryClientProvider, { client }, children),
	};
}

describe("useDocumentList", () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it("merges pages by following next_cursor across fetchNextPage", async () => {
		const page1: DocumentListPage = {
			items: [
				{
					id: "Single_JKHY/2010/page_28.pdf-3",
					ticker: "JKHY",
					year: 2010,
					page: 28,
					title: "JKHY 2010 page 28",
				},
			],
			next_cursor: "cursor-2",
		};
		const page2: DocumentListPage = {
			items: [
				{
					id: "Single_JKHY/2011/page_5.pdf-1",
					ticker: "JKHY",
					year: 2011,
					page: 5,
					title: "JKHY 2011 page 5",
				},
			],
			next_cursor: null,
		};

		const fetchMock = vi
			.fn()
			.mockResolvedValueOnce(jsonResponse(page1))
			.mockResolvedValueOnce(jsonResponse(page2));
		vi.stubGlobal("fetch", fetchMock);

		const { result } = renderHook(() => useDocumentList({ q: "jkhy" }), {
			wrapper: withQueryClient().wrapper,
		});

		await waitFor(() => {
			expect(result.current.isSuccess).toBe(true);
		});
		expect(fetchMock.mock.calls[0]?.[0]).toBe("/v1/documents?q=jkhy");
		expect(result.current.hasNextPage).toBe(true);

		await result.current.fetchNextPage();

		await waitFor(() => {
			expect(fetchMock).toHaveBeenCalledTimes(2);
		});
		await waitFor(() => {
			expect(result.current.data?.pages.length).toBe(2);
		});

		expect(fetchMock.mock.calls[1]?.[0]).toBe(
			"/v1/documents?q=jkhy&cursor=cursor-2",
		);

		const flattened = result.current.data?.pages.flatMap((p) => p.items) ?? [];
		expect(flattened.map((item) => item.id)).toEqual([
			"Single_JKHY/2010/page_28.pdf-3",
			"Single_JKHY/2011/page_5.pdf-1",
		]);
		expect(result.current.hasNextPage).toBe(false);
	});
});

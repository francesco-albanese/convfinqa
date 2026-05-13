import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DocPicker } from "@/components/DocPicker";
import type { DocumentListPage } from "@/lib/queries/documents";

function jsonResponse(body: DocumentListPage): Response {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

function renderDocPicker(overrides: { onSelect?: (id: string) => void } = {}) {
	const onSelect = overrides.onSelect ?? vi.fn();
	const onOpenChange = vi.fn();
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	render(
		<QueryClientProvider client={queryClient}>
			<DocPicker open onOpenChange={onOpenChange} onSelect={onSelect} />
		</QueryClientProvider>,
	);
	return { onSelect, onOpenChange };
}

const SAMPLE_PAGE: DocumentListPage = {
	items: [
		{
			id: "Single_JKHY/2010/page_28.pdf-3",
			ticker: "JKHY",
			year: 2010,
			page: 28,
			title: "JKHY 2010 page 28",
		},
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

describe("DocPicker", () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it("debounces the search input and refetches with the typed query", async () => {
		const fetchMock = vi.fn().mockResolvedValue(jsonResponse(SAMPLE_PAGE));
		vi.stubGlobal("fetch", fetchMock);
		const user = userEvent.setup();

		renderDocPicker();

		await waitFor(() => {
			expect(fetchMock).toHaveBeenCalled();
		});
		expect(fetchMock.mock.calls[0]?.[0]).toBe("/v1/documents");

		const input = screen.getByRole("searchbox", {
			name: /search documents/i,
		});
		await user.type(input, "jkhy");

		expect(
			fetchMock.mock.calls.some(([url]) => String(url).includes("q=jkhy")),
		).toBe(false);

		await waitFor(
			() => {
				expect(
					fetchMock.mock.calls.some(([url]) => String(url).includes("q=jkhy")),
				).toBe(true);
			},
			{ timeout: 1000 },
		);
	});

	it("calls onSelect with the document id when a result row is clicked", async () => {
		const fetchMock = vi.fn().mockResolvedValue(jsonResponse(SAMPLE_PAGE));
		vi.stubGlobal("fetch", fetchMock);
		const user = userEvent.setup();

		const { onSelect, onOpenChange } = renderDocPicker();

		const firstResult = await screen.findByRole("option", {
			name: /jkhy 2010 page 28/i,
		});
		await user.click(firstResult);

		expect(onSelect).toHaveBeenCalledTimes(1);
		expect(onSelect).toHaveBeenCalledWith("Single_JKHY/2010/page_28.pdf-3");
		expect(onOpenChange).toHaveBeenCalledWith(false);
	});

	it("omits year_min/year_max from the request when the slider is at default bounds", async () => {
		const fetchMock = vi.fn().mockResolvedValue(jsonResponse(SAMPLE_PAGE));
		vi.stubGlobal("fetch", fetchMock);

		renderDocPicker();

		await waitFor(() => {
			expect(fetchMock).toHaveBeenCalled();
		});
		const firstCall = String(fetchMock.mock.calls[0]?.[0] ?? "");
		expect(firstCall).not.toContain("year_min");
		expect(firstCall).not.toContain("year_max");
	});
});

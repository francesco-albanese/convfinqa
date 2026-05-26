import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RightPanel } from "@/components/RightPanel";
import type { Document } from "@/lib/queries/documents";

function jsonResponse(body: unknown): Response {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

function renderRightPanel(documentId: string, onChangeDocument = vi.fn()) {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const result = render(
		<QueryClientProvider client={queryClient}>
			<RightPanel documentId={documentId} onChangeDocument={onChangeDocument} />
		</QueryClientProvider>,
	);
	return { ...result, onChangeDocument };
}

const SAMPLE_DOCUMENT: Document = {
	id: "Single_JKHY/2009/page_28.pdf-3",
	ticker: "JKHY",
	year: 2009,
	page: 28,
	title: "JKHY 2009 page 28",
	pre_text: "Cash flow analysis for fiscal 2009.",
	post_text: "Refer to footnote 4 for additional context.",
	column_order: ["Year ended June 30, 2009", "2008", "2007"],
	conv_questions: null,
	table_data: {
		"Year ended June 30, 2009": {
			"net cash from operating activities": 206588,
		},
		"2008": { "net cash from operating activities": 181001 },
		"2007": { "net cash from operating activities": 174247 },
	},
};

function installClipboardMock(): ReturnType<typeof vi.fn> {
	const writeText = vi.fn().mockResolvedValue(undefined);
	Object.defineProperty(navigator, "clipboard", {
		configurable: true,
		value: { writeText },
	});
	return writeText;
}

describe("RightPanel", () => {
	afterEach(() => {
		vi.unstubAllGlobals();
		vi.useRealTimers();
	});

	it("renders the document title in the header and the pre/post text alongside the table", async () => {
		const fetchMock = vi.fn().mockResolvedValue(jsonResponse(SAMPLE_DOCUMENT));
		vi.stubGlobal("fetch", fetchMock);

		renderRightPanel(SAMPLE_DOCUMENT.id);

		expect(
			await screen.findByRole("heading", { name: /jkhy 2009 page 28/i }),
		).toBeInTheDocument();
		expect(screen.getByTestId("right-panel-pre-text")).toHaveTextContent(
			"Cash flow analysis for fiscal 2009.",
		);
		expect(screen.getByTestId("right-panel-post-text")).toHaveTextContent(
			"Refer to footnote 4 for additional context.",
		);
		expect(screen.getByTestId("doc-table")).toBeInTheDocument();
	});

	it("invokes onChangeDocument when the header 'Change document' button is clicked", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockResolvedValue(jsonResponse(SAMPLE_DOCUMENT)),
		);
		const user = userEvent.setup();
		const onChangeDocument = vi.fn();

		renderRightPanel(SAMPLE_DOCUMENT.id, onChangeDocument);
		await screen.findByRole("heading", { name: /jkhy 2009 page 28/i });

		await user.click(screen.getByRole("button", { name: /change document/i }));

		expect(onChangeDocument).toHaveBeenCalledTimes(1);
	});

	it("writes the visible rows + columns as RFC-4180 CSV to the clipboard when Copy as CSV is clicked", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockResolvedValue(jsonResponse(SAMPLE_DOCUMENT)),
		);
		const user = userEvent.setup();
		const writeText = installClipboardMock();
		renderRightPanel(SAMPLE_DOCUMENT.id);
		await screen.findByTestId("doc-table");

		await user.click(screen.getByRole("button", { name: /copy as csv/i }));

		expect(writeText).toHaveBeenCalledTimes(1);
		const written = writeText.mock.calls[0]?.[0];
		expect(written).toBe(
			[
				',"Year ended June 30, 2009",2008,2007',
				"net cash from operating activities,206588,181001,174247",
			].join("\r\n"),
		);
		expect(
			await screen.findByRole("button", { name: /copied/i }),
		).toBeInTheDocument();
	});

	it("keeps the aside visible (with an error message) when the document fetch fails", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockResolvedValue(new Response("oops", { status: 500 })),
		);

		renderRightPanel("Single_JKHY/2009/page_28.pdf-3");

		expect(screen.getByLabelText("Pinned document")).toBeInTheDocument();
		await waitFor(() => {
			expect(screen.getByTestId("right-panel-error")).toBeInTheDocument();
		});
	});

	it("shows the loading status while the document is being fetched", () => {
		const pending = new Promise<Response>(() => {});
		vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending));

		renderRightPanel("Single_JKHY/2009/page_28.pdf-3");

		expect(screen.getByLabelText("Pinned document")).toBeInTheDocument();
		expect(screen.getByRole("status")).toHaveTextContent(/loading document/i);
	});

	it("surfaces a 'Copy failed' state when navigator.clipboard.writeText rejects", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockResolvedValue(jsonResponse(SAMPLE_DOCUMENT)),
		);
		const user = userEvent.setup();
		const writeText = vi
			.fn()
			.mockRejectedValue(new Error("clipboard permission denied"));
		Object.defineProperty(navigator, "clipboard", {
			configurable: true,
			value: { writeText },
		});
		renderRightPanel(SAMPLE_DOCUMENT.id);
		await screen.findByTestId("doc-table");

		await user.click(screen.getByRole("button", { name: /copy as csv/i }));

		expect(
			await screen.findByRole("button", { name: /copy failed/i }),
		).toBeInTheDocument();
	});

	it("renders an empty-table notice when the document has no structured table", async () => {
		const documentWithoutTable: Document = {
			...SAMPLE_DOCUMENT,
			table_data: null,
			column_order: null,
		};
		vi.stubGlobal(
			"fetch",
			vi.fn().mockResolvedValue(jsonResponse(documentWithoutTable)),
		);

		renderRightPanel(SAMPLE_DOCUMENT.id);

		expect(
			await screen.findByTestId("right-panel-empty-table"),
		).toBeInTheDocument();
		expect(screen.queryByTestId("doc-table")).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /copy as csv/i }),
		).not.toBeInTheDocument();
	});
});

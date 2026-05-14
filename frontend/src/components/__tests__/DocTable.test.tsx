import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DocTable } from "@/components/DocTable";
import {
	type TableInput,
	tableToRowMajor,
} from "@/lib/transforms/tableToRowMajor";

describe("DocTable", () => {
	it("renders header columns and row labels from a row-major dataset", () => {
		const table = tableToRowMajor({
			"FY 2009": {
				"net income": 103102,
				"net cash from operating activities": 206588,
			},
			"FY 2008": {
				"net income": 104222,
				"net cash from operating activities": 181001,
			},
		});

		render(<DocTable table={table} />);

		const headers = screen
			.getAllByTestId("doc-table-header")
			.map((th) => th.textContent);
		expect(headers).toEqual(["FY 2009", "FY 2008"]);

		const rowLabels = screen
			.getAllByTestId("doc-table-row-label")
			.map((th) => th.textContent);
		expect(rowLabels).toEqual([
			"net income",
			"net cash from operating activities",
		]);

		const grid = screen.getByTestId("doc-table");
		expect(within(grid).getByText("103,102")).toBeInTheDocument();
		expect(within(grid).getByText("206,588")).toBeInTheDocument();
	});

	it("renders the columns in the wire order supplied by column_order even when JSON.parse reorders integer-like keys", () => {
		const wireOrder = ["Year ended June 30, 2009", "2008", "2007"];
		const parsed = JSON.parse(
			'{"Year ended June 30, 2009":{"net cash from operating activities":206588},"2008":{"net cash from operating activities":181001},"2007":{"net cash from operating activities":174247}}',
		) as TableInput;

		expect(Object.keys(parsed)).toEqual([
			"2007",
			"2008",
			"Year ended June 30, 2009",
		]);

		const table = tableToRowMajor(parsed, wireOrder);
		render(<DocTable table={table} />);

		const renderedHeaders = screen
			.getAllByTestId("doc-table-header")
			.map((th) => th.textContent);
		expect(renderedHeaders).toEqual(wireOrder);

		const cells = screen
			.getAllByTestId("doc-table-cell")
			.map((td) => td.textContent);
		expect(cells).toEqual(["206,588", "181,001", "174,247"]);
	});

	it("keeps the first column sticky at the left edge so wide tables stay legible", () => {
		const table = tableToRowMajor({
			"FY 2009": { "net income": 103102 },
			"FY 2008": { "net income": 104222 },
		});

		render(<DocTable table={table} />);

		const labelHeader = screen.getByTestId("doc-table-header-label");
		const labelHeaderStyle = window.getComputedStyle(labelHeader);
		expect(labelHeaderStyle.position).toBe("sticky");
		expect(labelHeaderStyle.left).toBe("0px");

		const rowLabel = screen.getAllByTestId("doc-table-row-label")[0];
		const rowLabelStyle = window.getComputedStyle(rowLabel as HTMLElement);
		expect(rowLabelStyle.position).toBe("sticky");
		expect(rowLabelStyle.left).toBe("0px");
	});

	it("right-aligns numeric cells with the monospace numeric utility and renders null as an em dash", () => {
		const table = tableToRowMajor({
			"FY 2009": { revenue: 103102, status: "n/a" },
			"FY 2008": { revenue: null, status: "filed" },
		});

		render(<DocTable table={table} />);

		const revenueRow = screen
			.getByText("revenue")
			.closest("tr") as HTMLTableRowElement;
		const revenueCells = within(revenueRow).getAllByTestId("doc-table-cell");
		expect(revenueCells[0]?.textContent).toBe("103,102");
		expect(revenueCells[0]).toHaveClass("text-right");
		expect(revenueCells[0]).toHaveClass("numeric");
		expect(revenueCells[1]?.textContent).toBe("—");

		const statusRow = screen
			.getByText("status")
			.closest("tr") as HTMLTableRowElement;
		const statusCells = within(statusRow).getAllByTestId("doc-table-cell");
		expect(statusCells[0]?.textContent).toBe("n/a");
		expect(statusCells[0]).not.toHaveClass("numeric");
		expect(statusCells[0]).not.toHaveClass("text-right");
	});

	it("wraps long header text so wide column names do not blow out the layout", () => {
		const table = tableToRowMajor({
			"Year ended June 30, 2009": { revenue: 1 },
			"Year ended June 30, 2008": { revenue: 2 },
		});

		render(<DocTable table={table} />);

		for (const header of screen.getAllByTestId("doc-table-header")) {
			expect(header).toHaveClass("break-words");
			expect(header).toHaveClass("whitespace-normal");
		}
	});
});

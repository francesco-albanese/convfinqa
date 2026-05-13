import { describe, expect, it } from "vitest";
import { rowMajorToCsv } from "@/lib/transforms/rowMajorToCsv";
import { tableToRowMajor } from "@/lib/transforms/tableToRowMajor";

describe("rowMajorToCsv", () => {
	it("serialises a JKHY-shaped table with raw numeric values and a header row", () => {
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

		const csv = rowMajorToCsv(table);

		expect(csv).toBe(
			[
				",FY 2009,FY 2008",
				"net income,103102,104222",
				"net cash from operating activities,206588,181001",
			].join("\r\n"),
		);
	});

	it("quotes fields that contain commas, quotes, or newlines and doubles internal quotes", () => {
		const table = tableToRowMajor({
			'Header, with "quotes"\nand newline': {
				"row, label": "value, with comma",
			},
		});

		const csv = rowMajorToCsv(table);

		expect(csv).toBe(
			[
				',"Header, with ""quotes""\nand newline"',
				'"row, label","value, with comma"',
			].join("\r\n"),
		);
	});

	it("emits empty strings for null cells (not the em dash the UI shows)", () => {
		const table = tableToRowMajor({
			"FY 2009": { revenue: null },
			"FY 2008": { revenue: 100 },
		});

		const csv = rowMajorToCsv(table);

		expect(csv).toBe(["," + "FY 2009,FY 2008", "revenue,,100"].join("\r\n"));
	});

	it("neutralises CSV-injection prefixes on string cells, row labels, and column headers", () => {
		const table = tableToRowMajor({
			"=cmd|'/c calc'!A0": {
				"-net change in cash": '=HYPERLINK("http://evil","x")',
				"+sum trick": "@SUM(A1:A9)",
			},
		});

		const csv = rowMajorToCsv(table);

		expect(csv).toBe(
			[
				`,'=cmd|'/c calc'!A0`,
				`'-net change in cash,"'=HYPERLINK(""http://evil"",""x"")"`,
				`'+sum trick,'@SUM(A1:A9)`,
			].join("\r\n"),
		);
	});

	it("leaves numeric values (including negatives) untouched so spreadsheets keep them as numbers", () => {
		const table = tableToRowMajor({
			"FY 2009": { "operating cash flow": -2913 },
		});

		const csv = rowMajorToCsv(table);

		expect(csv).toBe(
			["," + "FY 2009", "operating cash flow,-2913"].join("\r\n"),
		);
	});

	it("preserves the column order supplied to tableToRowMajor", () => {
		const wireOrder = ["Year ended June 30, 2009", "2008", "2007"];
		const parsed = JSON.parse(
			'{"Year ended June 30, 2009":{"net income":103102},"2008":{"net income":104222},"2007":{"net income":104681}}',
		);
		const table = tableToRowMajor(parsed, wireOrder);

		const csv = rowMajorToCsv(table);

		expect(csv.split("\r\n")[0]).toBe(',"Year ended June 30, 2009",2008,2007');
	});
});

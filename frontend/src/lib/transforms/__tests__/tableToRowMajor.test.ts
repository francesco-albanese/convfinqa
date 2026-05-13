import { describe, expect, it } from "vitest";
import {
	type TableInput,
	tableToRowMajor,
} from "@/lib/transforms/tableToRowMajor";

describe("tableToRowMajor", () => {
	it("converts a JKHY 2009 cash-flow shape into a row-major grid", () => {
		const input: TableInput = {
			"FY 2009": {
				"net income": 103102,
				"non-cash expenses": 74397,
				"change in receivables": 21214,
				"net cash from operating activities": 206588,
			},
			"FY 2008": {
				"net income": 104222,
				"non-cash expenses": 70420,
				"change in receivables": -2913,
				"net cash from operating activities": 181001,
			},
			"FY 2007": {
				"net income": 104681,
				"non-cash expenses": 56348,
				"change in receivables": -28853,
				"net cash from operating activities": 174247,
			},
		};

		const result = tableToRowMajor(input);

		expect(result.columns).toEqual(["FY 2009", "FY 2008", "FY 2007"]);
		expect(result.rowLabels).toEqual([
			"net income",
			"non-cash expenses",
			"change in receivables",
			"net cash from operating activities",
		]);
		expect(result.data).toEqual([
			[103102, 104222, 104681],
			[74397, 70420, 56348],
			[21214, -2913, -28853],
			[206588, 181001, 174247],
		]);
	});

	it("fills missing cells with null when a column does not declare every row label", () => {
		const input: TableInput = {
			"2024": { revenue: 100, costs: 60 },
			"2025": { revenue: 120 },
			"2026": { costs: 80, taxes: 12 },
		};

		const result = tableToRowMajor(input);

		expect(result.rowLabels).toEqual(["revenue", "costs", "taxes"]);
		expect(result.data).toEqual([
			[100, 120, null],
			[60, null, 80],
			[null, null, 12],
		]);
	});

	it("preserves the column order from the input object's insertion order", () => {
		const ordered: TableInput = {
			zeta: { a: 1 },
			alpha: { a: 2 },
			mu: { a: 3 },
		};

		expect(tableToRowMajor(ordered).columns).toEqual(["zeta", "alpha", "mu"]);

		const reordered: TableInput = {
			mu: { a: 3 },
			zeta: { a: 1 },
			alpha: { a: 2 },
		};

		expect(tableToRowMajor(reordered).columns).toEqual(["mu", "zeta", "alpha"]);
	});

	it("preserves explicit null and zero cells without coercing them", () => {
		const input: TableInput = {
			"2025": { a: 0, b: null, c: "n/a" },
		};

		const result = tableToRowMajor(input);

		expect(result.data).toEqual([[0], [null], ["n/a"]]);
	});

	it("uses the explicit columnOrder to restore wire order when integer-like keys were reordered by JS", () => {
		const wireOrder = ["Year ended June 30, 2009", "2008", "2007"];
		const parsed: TableInput = JSON.parse(
			'{"Year ended June 30, 2009":{"net income":103102},"2008":{"net income":104222},"2007":{"net income":104681}}',
		);

		expect(Object.keys(parsed)).toEqual([
			"2007",
			"2008",
			"Year ended June 30, 2009",
		]);

		const result = tableToRowMajor(parsed, wireOrder);

		expect(result.columns).toEqual(wireOrder);
		expect(result.data).toEqual([[103102, 104222, 104681]]);
	});

	it("ignores columns in columnOrder that are not present in the input", () => {
		const input: TableInput = {
			"2024": { revenue: 100 },
			"2025": { revenue: 200 },
		};

		const result = tableToRowMajor(input, ["2025", "missing", "2024"]);

		expect(result.columns).toEqual(["2025", "2024"]);
		expect(result.data).toEqual([[200, 100]]);
	});

	it("appends input columns missing from columnOrder so no data is dropped silently", () => {
		const input: TableInput = {
			alpha: { x: 1 },
			beta: { x: 2 },
			gamma: { x: 3 },
		};

		const result = tableToRowMajor(input, ["beta"]);

		expect(result.columns).toEqual(["beta", "alpha", "gamma"]);
		expect(result.data).toEqual([[2, 1, 3]]);
	});

	it("falls back to input insertion order when columnOrder is null", () => {
		const input: TableInput = {
			alpha: { x: 1 },
			beta: { x: 2 },
		};

		const result = tableToRowMajor(input, null);

		expect(result.columns).toEqual(["alpha", "beta"]);
	});

	it("falls back to input insertion order when columnOrder is an empty array", () => {
		const input: TableInput = {
			alpha: { x: 1 },
			beta: { x: 2 },
		};

		const result = tableToRowMajor(input, []);

		expect(result.columns).toEqual(["alpha", "beta"]);
	});
});

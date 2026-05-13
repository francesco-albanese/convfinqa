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
});

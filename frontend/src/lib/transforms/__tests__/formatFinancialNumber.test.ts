import { describe, expect, it } from "vitest";
import { formatFinancialNumber } from "@/lib/transforms/formatFinancialNumber";

describe("formatFinancialNumber", () => {
	it("preserves two-decimal precision for values like 1.23", () => {
		expect(formatFinancialNumber(1.23)).toBe("1.23");
	});

	it("preserves up to four decimals for values like 1.2345", () => {
		expect(formatFinancialNumber(1.2345)).toBe("1.2345");
	});

	it("rounds half-away when the value exceeds four fractional digits", () => {
		expect(formatFinancialNumber(1.23456)).toBe("1.2346");
	});

	it("drops trailing zeros — financial display does not pad to a fixed scale", () => {
		expect(formatFinancialNumber(1.2)).toBe("1.2");
		expect(formatFinancialNumber(1.0)).toBe("1");
	});

	it("inserts thousands separators on integers and on negatives", () => {
		expect(formatFinancialNumber(103102)).toBe("103,102");
		expect(formatFinancialNumber(-2913)).toBe("-2,913");
	});

	it("returns Infinity/-Infinity/NaN as plain strings so they surface in the UI instead of breaking Intl", () => {
		expect(formatFinancialNumber(Number.POSITIVE_INFINITY)).toBe("Infinity");
		expect(formatFinancialNumber(Number.NEGATIVE_INFINITY)).toBe("-Infinity");
		expect(formatFinancialNumber(Number.NaN)).toBe("NaN");
	});
});

import { describe, expect, it } from "vitest";
import { LayoutSearchSchema } from "@/lib/layout/schemas";

describe("LayoutSearchSchema", () => {
	it("accepts a missing documentId and yields an empty object", () => {
		expect(LayoutSearchSchema.parse({})).toEqual({});
	});

	it("accepts a non-empty string documentId", () => {
		expect(
			LayoutSearchSchema.parse({ documentId: "single_NKE/2010/page_X" }),
		).toEqual({ documentId: "single_NKE/2010/page_X" });
	});

	it("rejects an empty-string documentId", () => {
		expect(LayoutSearchSchema.safeParse({ documentId: "" }).success).toBe(
			false,
		);
	});

	it("rejects a non-string documentId", () => {
		expect(LayoutSearchSchema.safeParse({ documentId: 42 }).success).toBe(
			false,
		);
	});
});

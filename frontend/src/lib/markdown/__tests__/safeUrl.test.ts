import { describe, expect, it } from "vitest";
import { safeUrlTransform } from "@/lib/markdown/safeUrl";

describe("safeUrlTransform", () => {
	it.each([
		["https://example.com/path?q=1", "https://example.com/path?q=1"],
		["http://example.com", "http://example.com"],
		["mailto:user@example.com", "mailto:user@example.com"],
		["/relative/path", "/relative/path"],
		["#anchor", "#anchor"],
		["?query=1", "?query=1"],
		["plain-text-no-protocol", "plain-text-no-protocol"],
	])("passes through safe url %s", (input, expected) => {
		expect(safeUrlTransform(input)).toBe(expected);
	});

	it.each([
		"javascript:alert(1)",
		"JAVASCRIPT:alert(1)",
		"data:text/html,<script>alert(1)</script>",
		"data:image/png;base64,iVBORw0KGgo=",
		"file:///etc/passwd",
		"vbscript:msgbox(1)",
		"chrome://settings",
	])("drops dangerous url %s", (input) => {
		expect(safeUrlTransform(input)).toBe("");
	});
});

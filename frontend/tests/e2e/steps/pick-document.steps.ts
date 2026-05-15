import { expect, type Page } from "@playwright/test";
import { createBdd } from "playwright-bdd";

const { Given, When, Then } = createBdd();

type SeededDoc = {
	id: string;
	ticker: string;
	year: number;
	page: number;
	title: string;
};

const YEAR_DEFAULT_MIN = 2000;
const YEAR_DEFAULT_MAX = 2025;

const SEEDED_DOCS: SeededDoc[] = buildSeededDocs();

function buildSeededDocs(): SeededDoc[] {
	const plan: Array<[string, number[]]> = [
		["JKHY", [2008, 2009, 2010, 2011]],
		["NKE", [2009, 2010, 2011, 2012]],
		["AAPL", [2011, 2012, 2013, 2014]],
		["MSFT", [2012, 2013, 2014, 2015]],
		["GOOG", [2013, 2014, 2015, 2016]],
	];
	return plan.flatMap(([ticker, years]) =>
		years.map<SeededDoc>((year, index) => ({
			id: `Single_${ticker}/${year}/page_${28 + index}.pdf-1`,
			ticker,
			year,
			page: 28 + index,
			title: `${ticker} ${year} page ${28 + index}`,
		})),
	);
}

function matchesQuery(doc: SeededDoc, query: string): boolean {
	if (!query) return true;
	const needle = query.toLowerCase();
	return (
		doc.ticker.toLowerCase().includes(needle) ||
		doc.title.toLowerCase().includes(needle)
	);
}

function inYearRange(doc: SeededDoc, min: number, max: number): boolean {
	return doc.year >= min && doc.year <= max;
}

async function stubSeededDocumentList(page: Page): Promise<void> {
	await page.route(
		(url) => url.pathname === "/api/v1/documents",
		async (route, request) => {
			const url = new URL(request.url());
			const q = url.searchParams.get("q") ?? "";
			const yearMin = Number(
				url.searchParams.get("year_min") ?? YEAR_DEFAULT_MIN,
			);
			const yearMax = Number(
				url.searchParams.get("year_max") ?? YEAR_DEFAULT_MAX,
			);
			const items = SEEDED_DOCS.filter(
				(doc) => matchesQuery(doc, q) && inYearRange(doc, yearMin, yearMax),
			);
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ items, next_cursor: null }),
			});
		},
	);
}

async function visibleResultIds(page: Page): Promise<string[]> {
	return page
		.locator('[data-testid="doc-picker-result"]')
		.evaluateAll((nodes) =>
			nodes.map((node) => node.getAttribute("data-doc-id") ?? ""),
		);
}

async function adjustSliderThumb(
	page: Page,
	thumbIndex: number,
	key: "ArrowLeft" | "ArrowRight",
	presses: number,
): Promise<void> {
	const thumb = page.getByRole("slider").nth(thumbIndex);
	await thumb.focus();
	for (let i = 0; i < presses; i += 1) {
		await thumb.press(key);
	}
}

Given(
	"a stubbed backend with 20 deterministic documents seeded",
	async ({ page }) => {
		expect(SEEDED_DOCS.length).toBeGreaterThanOrEqual(20);
		await stubSeededDocumentList(page);
	},
);

When(
	"I type {string} into the document search",
	async ({ page }, text: string) => {
		await page.getByRole("searchbox").fill(text);
	},
);

When(
	"I narrow the year range to {int} through {int}",
	async ({ page }, lower: number, upper: number) => {
		await adjustSliderThumb(
			page,
			0,
			"ArrowRight",
			Math.max(0, lower - YEAR_DEFAULT_MIN),
		);
		await adjustSliderThumb(
			page,
			1,
			"ArrowLeft",
			Math.max(0, YEAR_DEFAULT_MAX - upper),
		);
	},
);

When("I pin the first picker result", async ({ page }) => {
	const firstResult = page.locator('[data-testid="doc-picker-result"]').first();
	await expect(firstResult).toBeVisible();
	await firstResult.click();
});

Then(
	"the picker shows only documents with ticker {string}",
	async ({ page }, ticker: string) => {
		const expected = SEEDED_DOCS.filter((doc) => doc.ticker === ticker).map(
			(doc) => doc.id,
		);
		expect(expected.length).toBeGreaterThan(0);
		await expect.poll(() => visibleResultIds(page)).toEqual(expected);
	},
);

Then(
	"the picker shows only documents whose year is between {int} and {int}",
	async ({ page }, lower: number, upper: number) => {
		const expected = SEEDED_DOCS.filter((doc) =>
			inYearRange(doc, lower, upper),
		).map((doc) => doc.id);
		expect(expected.length).toBeGreaterThan(0);
		await expect.poll(() => visibleResultIds(page)).toEqual(expected);
	},
);

Then(
	"the URL has the documentId search param set to the first picker result's id",
	async ({ page }) => {
		const firstId = SEEDED_DOCS[0]?.id ?? "";
		await expect(page).toHaveURL(
			(url) => url.searchParams.get("documentId") === firstId,
		);
	},
);

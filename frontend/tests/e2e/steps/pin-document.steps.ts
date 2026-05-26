import { expect, type Page } from "@playwright/test";
import { createBdd } from "playwright-bdd";
import { seedAuthedSession } from "./_authedSession";

const { Given, When, Then } = createBdd();

const JKHY_DOCUMENT_ID = "Single_JKHY/2009/page_28.pdf-3";
const JKHY_DOCUMENT_TITLE = "JKHY 2009 page 28";

const JKHY_DOCUMENT = {
	id: JKHY_DOCUMENT_ID,
	ticker: "JKHY",
	year: 2009,
	page: 28,
	title: JKHY_DOCUMENT_TITLE,
	pre_text: "Cash flow analysis for fiscal 2009.",
	post_text: "Refer to footnote 4 for additional context.",
	conv_questions: null,
	column_order: ["Year ended June 30, 2009", "2008", "2007"],
	table_data: {
		"Year ended June 30, 2009": {
			"net cash from operating activities": 206588,
		},
		"2008": { "net cash from operating activities": 181001 },
		"2007": { "net cash from operating activities": 174247 },
	},
};

const JKHY_DOCUMENT_SUMMARY = {
	id: JKHY_DOCUMENT.id,
	ticker: JKHY_DOCUMENT.ticker,
	year: JKHY_DOCUMENT.year,
	page: JKHY_DOCUMENT.page,
	title: JKHY_DOCUMENT.title,
};

const JKHY_CSV = [
	',"Year ended June 30, 2009",2008,2007',
	"net cash from operating activities,206588,181001,174247",
].join("\r\n");

const JKHY_DETAIL_PATHNAME = `/api/v1/documents/${encodeURI(JKHY_DOCUMENT_ID)}`;

async function stubDocumentsBackend(page: Page): Promise<void> {
	await page.route(
		(url) => url.pathname === JKHY_DETAIL_PATHNAME,
		async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(JKHY_DOCUMENT),
			});
		},
	);
	await page.route(
		(url) => url.pathname === "/api/v1/documents",
		async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					items: [JKHY_DOCUMENT_SUMMARY],
					next_cursor: null,
				}),
			});
		},
	);
}

async function pinDocumentViaUrl(page: Page): Promise<void> {
	await seedAuthedSession(page);
	await page.goto(`/app?documentId=${encodeURIComponent(JKHY_DOCUMENT_ID)}`);
	await expect(page.getByTestId("right-panel")).toBeVisible();
	await expect(page.getByTestId("doc-table")).toBeVisible();
}

Given(
	"a stubbed backend with the JKHY 2009 page-28-3 document seeded",
	async ({ page }) => {
		await stubDocumentsBackend(page);
	},
);

Given(
	"I open the app with the JKHY 2009 page-28-3 document pinned",
	async ({ page }) => {
		await pinDocumentViaUrl(page);
	},
);

When("I open the document picker", async ({ page }) => {
	await page
		.getByTestId("empty-state")
		.getByRole("button", { name: "Pin a document" })
		.click();
	await expect(page.getByTestId("doc-picker")).toBeVisible();
});

When("I pin the JKHY 2009 page-28-3 result", async ({ page }) => {
	await page
		.locator(
			`[data-testid="doc-picker-result"][data-doc-id="${JKHY_DOCUMENT_ID}"]`,
		)
		.click();
});

When(
	"I widen the right panel by four shift-arrow-left presses",
	async ({ page }) => {
		const handle = page.getByTestId("resize-handle");
		await handle.focus();
		for (let press = 0; press < 4; press += 1) {
			await handle.press("Shift+ArrowLeft");
		}
		await expect(page.getByTestId("resizable-split")).toHaveCSS(
			"width",
			"608px",
		);
	},
);

Then(
	"the right panel renders the JKHY 2009 page-28-3 table",
	async ({ page }) => {
		await expect(
			page.getByRole("heading", { name: JKHY_DOCUMENT_TITLE }),
		).toBeVisible();
		await expect(page.getByTestId("doc-table")).toBeVisible();
	},
);

Then("the table shows the row {string}", async ({ page }, label: string) => {
	await expect(
		page
			.getByTestId("doc-table")
			.getByRole("rowheader", { name: label, exact: true }),
	).toBeVisible();
});

Then(
	"the right panel is {int} pixels wide",
	async ({ page }, pixels: number) => {
		await expect(page.getByTestId("resizable-split")).toHaveCSS(
			"width",
			`${pixels}px`,
		);
	},
);

type ClipboardGlobals = {
	navigator: { clipboard: { readText(): Promise<string> } };
};

Then(
	"the clipboard contains the JKHY 2009 page-28-3 CSV bytes",
	async ({ page }) => {
		await expect
			.poll(() =>
				page.evaluate(() =>
					(
						globalThis as unknown as ClipboardGlobals
					).navigator.clipboard.readText(),
				),
			)
			.toBe(JKHY_CSV);
	},
);

Then("the document picker is open", async ({ page }) => {
	await expect(page.getByTestId("doc-picker")).toBeVisible();
});

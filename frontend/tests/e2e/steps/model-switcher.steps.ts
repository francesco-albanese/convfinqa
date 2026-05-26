import { expect, type Page } from "@playwright/test";
import { createBdd } from "playwright-bdd";
import { seedAuthedSession } from "./_authedSession";

const { Given, When, Then, Before } = createBdd();

let lastStreamModel: string | null = null;

Before(() => {
	lastStreamModel = null;
});

async function mockModels(
	page: Page,
	models: string[],
	fallback: string,
): Promise<void> {
	await page.route(
		(url) => url.pathname === "/api/v1/models",
		(route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ models, default: fallback }),
			}),
	);
}

async function mockChatStream(page: Page): Promise<void> {
	await page.route("**/v1/chat/stream", async (route, request) => {
		const payload = request.postDataJSON() as { model?: string } | null;
		lastStreamModel = payload?.model ?? null;
		const body = [
			`data: ${JSON.stringify({ type: "start", messageId: "m1" })}\n\n`,
			`data: ${JSON.stringify({ type: "text-start", id: "m1" })}\n\n`,
			`data: ${JSON.stringify({ type: "text-delta", id: "m1", delta: "ok" })}\n\n`,
			`data: ${JSON.stringify({ type: "text-end", id: "m1" })}\n\n`,
			`data: ${JSON.stringify({ type: "finish" })}\n\n`,
			"data: [DONE]\n\n",
		].join("");
		await route.fulfill({
			status: 200,
			headers: {
				"content-type": "text/event-stream",
				"cache-control": "no-cache",
				"x-vercel-ai-ui-message-stream": "v1",
			},
			body,
		});
	});
}

Given(
	"a backend offering models {string}, {string} defaulting to {string}",
	async ({ page }, first: string, second: string, fallback: string) => {
		await mockModels(page, [first, second], fallback);
		await mockChatStream(page);
	},
);

Given(
	"I open the chat for model switching with document {string}",
	async ({ page }, documentId: string) => {
		await seedAuthedSession(page);
		await page.goto(`/app?documentId=${encodeURIComponent(documentId)}`);
		await expect(page.getByRole("textbox", { name: "Message" })).toBeVisible();
	},
);

When("I select the model {string}", async ({ page }, model: string) => {
	await page.getByLabel("Model").selectOption(model);
});

When("I send {string} from the composer", async ({ page }, message: string) => {
	const composer = page.getByRole("textbox", { name: "Message" });
	await composer.click();
	await composer.fill(message);
	await composer.press("Meta+Enter");
});

When("I reload the app", async ({ page }) => {
	await page.reload();
	await expect(page.getByLabel("Model")).toBeVisible();
});

Then(
	"the chat stream request used model {string}",
	async ({ page: _page }, model: string) => {
		await expect.poll(() => lastStreamModel).toBe(model);
	},
);

Then("the model picker shows {string}", async ({ page }, model: string) => {
	await expect(page.getByLabel("Model")).toHaveValue(model);
});

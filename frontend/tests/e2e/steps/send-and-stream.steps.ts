import { expect, type Page } from "@playwright/test";
import { createBdd } from "playwright-bdd";
import { seedAuthedSession } from "./_authedSession";

const { Given, When, Then } = createBdd();

type SseFrame = {
	type: string;
	[key: string]: unknown;
};

function buildSseBody(frames: SseFrame[]): string {
	const lines = frames.map((frame) => `data: ${JSON.stringify(frame)}\n\n`);
	return `${lines.join("")}data: [DONE]\n\n`;
}

async function stubChatStream(
	page: Page,
	{ text, conversationId }: { text: string; conversationId: string },
): Promise<void> {
	await page.route("**/v1/chat/stream", async (route) => {
		const body = buildSseBody([
			{ type: "start", messageId: "msg-1" },
			{
				type: "data-conversation",
				data: { conversationId },
			},
			{ type: "text-start", id: "msg-1" },
			{ type: "text-delta", id: "msg-1", delta: text },
			{ type: "text-end", id: "msg-1" },
			{ type: "finish" },
		]);
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
	"a stubbed backend that streams {string} with conversation id {string}",
	async ({ page }, text: string, conversationId: string) => {
		await stubChatStream(page, { text, conversationId });
	},
);

Given(
	"I open the chat with a pinned document {string}",
	async ({ page }, documentId: string) => {
		await seedAuthedSession(page);
		await page.goto(`/app?documentId=${encodeURIComponent(documentId)}`);
		await expect(page.getByRole("textbox", { name: "Message" })).toBeVisible();
	},
);

When("I type {string} in the composer", async ({ page }, message: string) => {
	const composer = page.getByRole("textbox", { name: "Message" });
	await composer.click();
	await composer.fill(message);
});

When("I press Cmd+Enter", async ({ page }) => {
	await page.getByRole("textbox", { name: "Message" }).press("Meta+Enter");
});

Then(
	"I see my message {string} in the conversation",
	async ({ page }, message: string) => {
		await expect(
			page.locator('[data-role="user"]').filter({ hasText: message }),
		).toBeVisible();
	},
);

Then(
	"I see the assistant reply containing {string}",
	async ({ page }, snippet: string) => {
		await expect(
			page.locator('[data-role="assistant"]').filter({ hasText: snippet }),
		).toBeVisible();
	},
);

Then("the URL contains {string}", async ({ page }, fragment: string) => {
	await expect.poll(() => page.url()).toContain(fragment);
});

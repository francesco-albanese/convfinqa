import { expect, type Page } from "@playwright/test";
import { createBdd } from "playwright-bdd";
import { seedAuthedSession } from "./_authedSession";

const { Given, When, Then, Before } = createBdd();

type SseFrame = {
	type: string;
	[key: string]: unknown;
};

type SidebarSummary = {
	id: string;
	document: {
		id: string;
		ticker: string | null;
		year: number | null;
		title: string | null;
	};
	title: string | null;
	last_message_preview: string;
	last_message_at: string;
};

const sidebarConversations = new Map<string, SidebarSummary>();

Before(() => {
	sidebarConversations.clear();
});

function buildSseBody(frames: SseFrame[]): string {
	const lines = frames.map((frame) => `data: ${JSON.stringify(frame)}\n\n`);
	return `${lines.join("")}data: [DONE]\n\n`;
}

async function stubChatStream(
	page: Page,
	{
		text,
		conversationId,
		title,
	}: { text: string; conversationId: string; title?: string },
): Promise<void> {
	await page.route("**/v1/chat/stream", async (route) => {
		if (title) {
			const existing = sidebarConversations.get(conversationId);
			if (existing) {
				sidebarConversations.set(conversationId, { ...existing, title });
			}
		}
		const frames: SseFrame[] = [
			{ type: "start", messageId: "msg-1" },
			{
				type: "data-conversation",
				data: { conversationId },
			},
			{ type: "text-start", id: "msg-1" },
			{ type: "text-delta", id: "msg-1", delta: text },
		];
		if (title) {
			frames.push({
				type: "data-title",
				data: { conversationId, title },
			});
		}
		const body = buildSseBody([
			...frames,
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

async function stubSidebarChats(page: Page): Promise<void> {
	await page.route("**/api/v1/chats", (route, request) => {
		if (request.method() !== "GET") return route.fallback();
		return route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({
				items: Array.from(sidebarConversations.values()),
			}),
		});
	});
}

Given(
	"a stubbed backend that streams {string} with conversation id {string}",
	async ({ page }, text: string, conversationId: string) => {
		await seedAuthedSession(page);
		await stubChatStream(page, { text, conversationId });
	},
);

Given(
	"a stubbed backend that streams {string} with conversation id {string} and title {string}",
	async ({ page }, text: string, conversationId: string, title: string) => {
		await seedAuthedSession(page);
		await stubChatStream(page, { text, conversationId, title });
	},
);

Given(
	"the sidebar already has conversation {string} with preview {string}",
	async ({ page }, conversationId: string, preview: string) => {
		await seedAuthedSession(page);
		sidebarConversations.set(conversationId, {
			id: conversationId,
			document: {
				id: "single_NKE/2010/page_X",
				ticker: "NKE",
				year: 2010,
				title: "NKE 2010",
			},
			title: null,
			last_message_preview: preview,
			last_message_at: new Date(Date.UTC(2026, 4, 14, 8, 0, 0)).toISOString(),
		});
		await stubSidebarChats(page);
	},
);

Given(
	"document {string} suggests {string} and {string}",
	async ({ page }, documentId: string, first: string, second: string) => {
		await seedAuthedSession(page);
		await page.route(
			(url) => {
				if (!url.pathname.startsWith("/api/v1/documents/")) return false;
				const id = decodeURIComponent(
					url.pathname.slice("/api/v1/documents/".length),
				);
				return id === documentId;
			},
			(route) =>
				route.fulfill({
					status: 200,
					contentType: "application/json",
					body: JSON.stringify({
						id: documentId,
						ticker: "NKE",
						year: 2010,
						page: 28,
						title: "NKE 2010",
						pre_text: "",
						post_text: "",
						table_data: null,
						column_order: null,
						conv_questions: [first, second],
					}),
				}),
		);
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

When(
	"I choose the suggested question {string}",
	async ({ page }, question: string) => {
		await page.getByRole("button", { name: question }).click();
	},
);

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

Then("the composer contains {string}", async ({ page }, text: string) => {
	await expect(page.getByRole("textbox", { name: "Message" })).toHaveValue(
		text,
	);
});

Then(
	"the sidebar conversation {string} is titled {string}",
	async ({ page }, conversationId: string, title: string) => {
		await expect(
			page
				.locator(
					`[data-testid="sidebar-chat-row"][data-chat-id="${conversationId}"]`,
				)
				.filter({ hasText: title }),
		).toBeVisible();
	},
);

Then(
	"I see the follow-up suggestion {string}",
	async ({ page }, question: string) => {
		await expect(page.getByText("try next")).toBeVisible();
		await expect(page.getByRole("button", { name: question })).toBeVisible();
	},
);

import { expect, type Page } from "@playwright/test";
import { createBdd } from "playwright-bdd";
import { seedAuthedSession } from "./_authedSession";

const { Given, When, Then, Before } = createBdd();

type SidebarSummary = {
	id: string;
	document: {
		id: string;
		ticker: string | null;
		year: number | null;
		title: string;
	};
	title: string | null;
	last_message_preview: string;
	last_message_at: string;
};

const conversations = new Map<string, SidebarSummary>();
const deletedConversationIds = new Set<string>();
let routesReady = false;

Before(() => {
	conversations.clear();
	deletedConversationIds.clear();
	routesReady = false;
});

function listBody(): { items: SidebarSummary[] } {
	const items = Array.from(conversations.values()).filter(
		(c) => !deletedConversationIds.has(c.id),
	);
	return { items };
}

async function ensureRoutes(page: Page): Promise<void> {
	if (routesReady) return;
	routesReady = true;

	await page.route(
		(url) => /^\/api\/v1\/chats\/[^/]+$/.test(url.pathname),
		async (route, request) => {
			if (request.method() !== "DELETE") return route.fallback();
			const id = decodeURIComponent(
				new URL(request.url()).pathname.split("/").pop() ?? "",
			);
			deletedConversationIds.add(id);
			await route.fulfill({ status: 204, body: "" });
		},
	);

	await page.route(
		(url) => /^\/api\/v1\/chats\/[^/]+\/messages$/.test(url.pathname),
		(route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ items: [] }),
			}),
	);

	await page.route(
		(url) => url.pathname === "/api/v1/chats",
		(route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(listBody()),
			}),
	);
}

function seedConversation(chatId: string, documentId: string): void {
	conversations.set(chatId, {
		id: chatId,
		document: {
			id: documentId,
			ticker: documentId.split("_")[1]?.split("/")[0] ?? null,
			year: null,
			title: documentId,
		},
		title: null,
		last_message_preview: "what was the net cash in 2009?",
		last_message_at: new Date(Date.UTC(2026, 4, 14, 8, 0, 0)).toISOString(),
	});
}

Given(
	"I am signed in viewing a pinned conversation {string} on document {string}",
	async ({ page }, chatId: string, documentId: string) => {
		await ensureRoutes(page);
		seedConversation(chatId, documentId);
		await seedAuthedSession(page);
		await page.goto(
			`/app?documentId=${encodeURIComponent(documentId)}&chatId=${chatId}`,
		);
		await expect(page.getByTestId("authed-shell")).toBeVisible();
	},
);

Given(
	"I am signed in with a sidebar conversation {string} on document {string}",
	async ({ page }, chatId: string, documentId: string) => {
		await ensureRoutes(page);
		seedConversation(chatId, documentId);
		await seedAuthedSession(page);
		await page.goto("/app");
		await expect(page.getByTestId("authed-shell")).toBeVisible();
	},
);

When("I start a new conversation from the sidebar", async ({ page }) => {
	await page.getByRole("button", { name: "New conversation" }).click();
});

When(
	"I delete the sidebar conversation {string} and confirm",
	async ({ page }, chatId: string) => {
		const row = page.locator(
			`[data-testid="sidebar-chat-row"][data-chat-id="${chatId}"]`,
		);
		await expect(row).toBeVisible();
		await page
			.locator(`[data-chat-id="${chatId}"]`)
			.locator(
				'xpath=following-sibling::button[@data-testid="sidebar-chat-delete"]',
			)
			.click();
		await page
			.getByRole("dialog")
			.getByRole("button", { name: "Delete" })
			.click();
	},
);

Then("the composer shows the {string} hint", async ({ page }, hint: string) => {
	await expect(page.getByRole("note")).toHaveText(hint);
});

Then("the URL no longer pins a document or a chat", async ({ page }) => {
	await expect.poll(() => page.url()).not.toContain("documentId");
	await expect.poll(() => page.url()).not.toContain("chatId");
});

Then(
	"a DELETE request was sent for conversation {string}",
	async ({ page: _page }, chatId: string) => {
		await expect.poll(() => deletedConversationIds.has(chatId)).toBe(true);
	},
);

Then(
	"the sidebar no longer lists conversation {string}",
	async ({ page }, chatId: string) => {
		await expect(
			page.locator(
				`[data-testid="sidebar-chat-row"][data-chat-id="${chatId}"]`,
			),
		).toHaveCount(0);
	},
);

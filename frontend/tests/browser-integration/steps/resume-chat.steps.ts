import { expect, type Page } from "@playwright/test";
import { createBdd, type DataTable } from "playwright-bdd";
import { seedAuthedSession } from "./_authedSession";

const { Given, When, Then, Before } = createBdd();

type PersistedMessage = {
	id: string;
	role: string;
	content: string;
	created_at: string;
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

const sidebarSummaries = new Map<string, SidebarSummary>();
const persistedMessages = new Map<string, PersistedMessage[]>();
const routedPages = new WeakSet<Page>();

Before(() => {
	sidebarSummaries.clear();
	persistedMessages.clear();
});

function summaryListBody(): { items: SidebarSummary[] } {
	const items = Array.from(sidebarSummaries.values()).sort((a, b) =>
		b.last_message_at.localeCompare(a.last_message_at),
	);
	return { items };
}

async function ensureChatsRoutes(page: Page): Promise<void> {
	if (routedPages.has(page)) return;
	routedPages.add(page);
	await page.route(
		(url) => url.pathname === "/api/v1/chats",
		async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify(summaryListBody()),
			});
		},
	);
	await page.route(
		(url) => /^\/api\/v1\/chats\/[^/]+\/messages$/.test(url.pathname),
		async (route, request) => {
			const path = new URL(request.url()).pathname;
			const match = path.match(/^\/api\/v1\/chats\/([^/]+)\/messages$/);
			const chatId = match ? decodeURIComponent(match[1] ?? "") : "";
			const items = persistedMessages.get(chatId) ?? [];
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ items }),
			});
		},
	);
}

Given(
	"a stubbed backend with a conversation {string} persisting these messages:",
	async ({ page }, chatId: string, table: DataTable) => {
		await seedAuthedSession(page);
		await ensureChatsRoutes(page);
		const rows = table.hashes();
		const messages: PersistedMessage[] = rows.map((row, index) => ({
			id: `${chatId}-msg-${index + 1}`,
			role: row.role ?? "assistant",
			content: row.content ?? "",
			created_at: new Date(Date.UTC(2026, 4, 14, 8, 0, index)).toISOString(),
		}));
		persistedMessages.set(chatId, messages);
	},
);

Given(
	"the conversation {string} is pinned to document {string} titled {string}",
	async ({ page }, chatId: string, documentId: string, title: string) => {
		await seedAuthedSession(page);
		await ensureChatsRoutes(page);
		const lastUser = (persistedMessages.get(chatId) ?? [])
			.filter((message) => message.role === "user")
			.at(-1);
		sidebarSummaries.set(chatId, {
			id: chatId,
			document: {
				id: documentId,
				ticker: title.split(" ")[0] ?? null,
				year: Number.parseInt(title.split(" ")[1] ?? "", 10) || null,
				title,
			},
			title: null,
			last_message_preview: (lastUser?.content ?? "").slice(0, 80),
			last_message_at: lastUser?.created_at ?? new Date().toISOString(),
		});
	},
);

Given("I open the app at {string}", async ({ page }, path: string) => {
	await seedAuthedSession(page);
	await ensureChatsRoutes(page);
	await page.goto(path);
	await expect(page.getByTestId("authed-shell")).toBeVisible();
});

Given(
	"the just-finished stream is recorded as a new sidebar conversation {string} with preview {string} pinned to document {string} titled {string}",
	async (
		{ page },
		chatId: string,
		preview: string,
		documentId: string,
		title: string,
	) => {
		await seedAuthedSession(page);
		await ensureChatsRoutes(page);
		sidebarSummaries.set(chatId, {
			id: chatId,
			document: {
				id: documentId,
				ticker: title.split(" ")[0] ?? null,
				year: Number.parseInt(title.split(" ")[1] ?? "", 10) || null,
				title,
			},
			title: null,
			last_message_preview: preview.slice(0, 80),
			last_message_at: new Date().toISOString(),
		});
		await page.route(
			(url) => url.pathname === "/api/v1/chat/stream",
			async (route) => {
				const body = [
					`data: ${JSON.stringify({ type: "start", messageId: "msg-resume" })}\n\n`,
					`data: ${JSON.stringify({ type: "data-conversation", data: { conversationId: chatId } })}\n\n`,
					`data: ${JSON.stringify({ type: "text-start", id: "msg-resume" })}\n\n`,
					`data: ${JSON.stringify({ type: "text-delta", id: "msg-resume", delta: "ok" })}\n\n`,
					`data: ${JSON.stringify({ type: "text-end", id: "msg-resume" })}\n\n`,
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
			},
		);
	},
);

When(
	"I click the sidebar conversation row for {string}",
	async ({ page }, chatId: string) => {
		const row = page.locator(
			`[data-testid="sidebar-chat-row"][data-chat-id="${chatId}"]`,
		);
		await expect(row).toBeVisible();
		await row.click();
	},
);

Then(
	"the sidebar shows a conversation row for {string} with the preview {string}",
	async ({ page }, chatId: string, preview: string) => {
		const row = page.locator(
			`[data-testid="sidebar-chat-row"][data-chat-id="${chatId}"]`,
		);
		await expect(row).toBeVisible();
		await expect(row).toContainText(preview);
	},
);

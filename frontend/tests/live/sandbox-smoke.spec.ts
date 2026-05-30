import { expect, type Page, test } from "@playwright/test";
import { getLiveE2eSettings } from "./settings";

const settings = getLiveE2eSettings();
const prompt = "Answer in one short sentence: what is this document about?";

function chatIdFromUrl(page: Page): string | null {
	return new URL(page.url()).searchParams.get("chatId");
}

function rememberCurrentChatId(
	page: Page,
	createdConversationIds: Set<string>,
): void {
	const chatId = chatIdFromUrl(page);
	if (chatId) createdConversationIds.add(chatId);
}

async function deleteConversationThroughUi(
	page: Page,
	chatId: string,
): Promise<void> {
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
	await expect(row).toHaveCount(0);
}

test("sandbox smoke chat persists, cleans up, and signs out", async ({
	page,
}) => {
	const createdConversationIds = new Set<string>();

	try {
		await page.goto(
			`/app?documentId=${encodeURIComponent(settings.documentId)}`,
		);
		await expect(page.getByTestId("authed-shell")).toBeVisible();

		const composer = page.getByRole("textbox", { name: "Message" });
		await composer.fill(prompt);
		await composer.press("Meta+Enter");

		await expect(
			page.locator('[data-role="user"]').filter({ hasText: prompt }),
		).toBeVisible();
		await expect(page.locator('[data-role="assistant"]')).toContainText(/\S/, {
			timeout: 90_000,
		});
		const assistantText = (
			await page.locator('[data-role="assistant"]').last().innerText()
		).trim();
		if (assistantText.length === 0) {
			throw new Error("Live smoke received an empty assistant response");
		}
		await expect(
			page.getByRole("button", { name: "Stop generating" }),
		).toHaveCount(0, { timeout: 90_000 });

		await expect
			.poll(() => chatIdFromUrl(page), { timeout: 30_000 })
			.not.toBeNull();
		const chatId = chatIdFromUrl(page);
		if (!chatId) throw new Error("Live smoke did not resolve a chatId");
		createdConversationIds.add(chatId);

		const row = page.locator(
			`[data-testid="sidebar-chat-row"][data-chat-id="${chatId}"]`,
		);
		await expect(row).toBeVisible();

		await page.reload();
		await expect(page.getByTestId("authed-shell")).toBeVisible();
		await expect(row).toBeVisible();
		await expect(page.locator('[data-role="assistant"]').last()).toContainText(
			assistantText,
		);
	} finally {
		rememberCurrentChatId(page, createdConversationIds);
		for (const chatId of createdConversationIds) {
			await deleteConversationThroughUi(page, chatId);
		}
	}

	await page.getByTestId("user-menu-trigger").click();
	await page.getByRole("menuitem", { name: /^sign out$/i }).click();
	await expect(page).toHaveURL(/\/sign-in(\b|\/|\?)/);
});

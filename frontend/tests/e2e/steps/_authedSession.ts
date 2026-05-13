import type { Page } from "@playwright/test";

const AUTH_STORAGE_KEY = "auth.userId";
const DEV_USER_ID = "dev-user-e2e";

type BrowserGlobals = {
	localStorage: { setItem(key: string, value: string): void };
};

export async function seedAuthedSession(page: Page): Promise<void> {
	await page.addInitScript(
		([key, value]) => {
			(globalThis as unknown as BrowserGlobals).localStorage.setItem(
				key,
				value,
			);
		},
		[AUTH_STORAGE_KEY, DEV_USER_ID] as const,
	);
}

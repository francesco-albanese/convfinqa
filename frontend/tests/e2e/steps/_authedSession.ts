import type { Page } from "@playwright/test";

const AUTH_STORAGE_KEY = "auth.userId";
const DEV_USER_ID = "dev-user-e2e";

type BrowserGlobals = {
	localStorage: { setItem(key: string, value: string): void };
};

export async function mockHealthz(page: Page): Promise<void> {
	await page.route("**/api/v1/healthz", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ status: "ok" }),
		}),
	);
}

export async function seedAuthedSession(page: Page): Promise<void> {
	await mockHealthz(page);
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

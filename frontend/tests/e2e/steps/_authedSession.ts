import type { Page } from "@playwright/test";

const E2E_USER_ID = "00000000-0000-0000-0000-000000000001";
const E2E_EMAIL = "e2e@example.com";

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
	await page.route("**/api/v1/me", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ user_id: E2E_USER_ID, email: E2E_EMAIL }),
		}),
	);
	await page.route("**/api/auth/refresh", (route) =>
		route.fulfill({ status: 401 }),
	);
	await page.route("**/api/auth/logout", (route) =>
		route.fulfill({ status: 204 }),
	);
}

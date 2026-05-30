import { mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import { expect, test } from "@playwright/test";
import { getLiveE2eSettings } from "./settings";

const settings = getLiveE2eSettings();

test("authenticate through Cognito Hosted UI", async ({ page }) => {
	await page.goto("/sign-in");
	const loginRequest = page.waitForRequest(
		(request) => new URL(request.url()).pathname === "/api/auth/login",
	);
	await page
		.getByRole("button", { name: /continue with (google|cognito)/i })
		.click();
	await loginRequest;

	await expect(page).toHaveURL(/amazoncognito\.com|\/oauth2\//);

	const username = page
		.getByLabel(/email|username/i)
		.or(page.locator('input[name="username"]'))
		.first();
	await username.fill(settings.email);

	const password = page
		.getByLabel(/password/i)
		.or(page.locator('input[name="password"]'))
		.first();
	await password.fill(settings.password);

	await page
		.getByRole("button", { name: /sign in|login|continue/i })
		.first()
		.click();

	await expect(page).toHaveURL(/\/app(\b|\/|\?)/, { timeout: 60_000 });
	await expect(page.getByTestId("authed-shell")).toBeVisible();

	await mkdir(dirname(settings.authStatePath), { recursive: true });
	await page.context().storageState({ path: settings.authStatePath });
});

import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";

const { Given, When, Then } = createBdd();

Given("I open the sign-in page", async ({ page }) => {
	await page.goto("/sign-in");
	await expect(
		page.getByRole("heading", { name: /welcome back/i }),
	).toBeVisible();
});

When("I click the {string} button", async ({ page }, label: string) => {
	await page
		.getByRole("button", { name: new RegExp(`^${label}$`, "i") })
		.click();
});

Then("I land on the app page", async ({ page }) => {
	await expect(page).toHaveURL(/\/app(\b|\/)/);
	await expect(page.getByTestId("authed-shell")).toBeVisible();
});

type BrowserGlobals = { localStorage: { getItem(key: string): string | null } };

Then("my dev user id is persisted", async ({ page }) => {
	const stored = await page.evaluate(() =>
		(globalThis as unknown as BrowserGlobals).localStorage.getItem(
			"auth.userId",
		),
	);
	expect(stored).toMatch(/^dev-user-/);
});

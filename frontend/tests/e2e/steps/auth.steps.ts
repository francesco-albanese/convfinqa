import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";
import { mockHealthz, seedAuthedSession } from "./_authedSession";

const { Given, When, Then } = createBdd();

Given("I open the sign-in page", async ({ page }) => {
	await mockHealthz(page);
	await page.goto("/sign-in");
	await expect(
		page.getByRole("heading", { name: /welcome back/i }),
	).toBeVisible();
});

Given("I am signed in on the app page", async ({ page }) => {
	await mockHealthz(page);
	await seedAuthedSession(page);
	await page.goto("/app");
	await expect(page.getByTestId("authed-shell")).toBeVisible();
});

When("I click the {string} button", async ({ page }, label: string) => {
	await page
		.getByRole("button", { name: new RegExp(`^${label}$`, "i") })
		.click();
});

When("I open the user menu", async ({ page }) => {
	await page.getByTestId("user-menu-trigger").click();
});

When("I select the {string} menu item", async ({ page }, label: string) => {
	await page
		.getByRole("menuitem", { name: new RegExp(`^${label}$`, "i") })
		.click();
});

Then("I land on the app page", async ({ page }) => {
	await expect(page).toHaveURL(/\/app(\b|\/)/);
	await expect(page.getByTestId("authed-shell")).toBeVisible();
});

Then("I land on the sign-in page", async ({ page }) => {
	await expect(page).toHaveURL(/\/sign-in(\b|\/)/);
	await expect(
		page.getByRole("heading", { name: /welcome back/i }),
	).toBeVisible();
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

Then("my dev user id is cleared", async ({ page }) => {
	const stored = await page.evaluate(() =>
		(globalThis as unknown as BrowserGlobals).localStorage.getItem(
			"auth.userId",
		),
	);
	expect(stored).toBeNull();
});

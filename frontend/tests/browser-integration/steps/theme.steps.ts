import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";

const { Given, When, Then } = createBdd();

const THEME_STORAGE_KEY = "convfinqa:theme.mode";

type BrowserGlobals = {
	localStorage: {
		setItem(key: string, value: string): void;
		removeItem(key: string): void;
	};
};

Given("my system prefers light", async ({ page }) => {
	await page.emulateMedia({ colorScheme: "light" });
});

Given("my system prefers dark", async ({ page }) => {
	await page.emulateMedia({ colorScheme: "dark" });
});

Given("I have not saved a theme preference", async ({ page }) => {
	await page.addInitScript((key) => {
		(globalThis as unknown as BrowserGlobals).localStorage.removeItem(key);
	}, THEME_STORAGE_KEY);
});

Given("I have saved {string} as my theme", async ({ page }, mode: string) => {
	await page.addInitScript(
		([key, value]) => {
			(globalThis as unknown as BrowserGlobals).localStorage.setItem(
				key,
				value,
			);
		},
		[THEME_STORAGE_KEY, mode] as const,
	);
});

When("I open the home page", async ({ page }) => {
	await page.goto("/");
});

When("I switch back to the system theme", async ({ page }) => {
	await page.evaluate(
		([key, value]) => {
			(globalThis as unknown as BrowserGlobals).localStorage.setItem(
				key,
				value,
			);
		},
		[THEME_STORAGE_KEY, "system"] as const,
	);
	await page.addInitScript(
		([key, value]) => {
			(globalThis as unknown as BrowserGlobals).localStorage.setItem(
				key,
				value,
			);
		},
		[THEME_STORAGE_KEY, "system"] as const,
	);
});

Then("the document theme is {string}", async ({ page }, expected: string) => {
	const html = page.locator("html");
	await expect(html).toHaveAttribute("data-theme", expected);
});

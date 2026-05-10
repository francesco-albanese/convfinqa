import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";

const { Given, Then } = createBdd();

Given("I open the home page", async ({ page }) => {
	await page.goto("/");
});

Then(
	"I see the {string} placeholder",
	async ({ page }, placeholder: string) => {
		await expect(
			page.getByRole("heading", { name: placeholder }),
		).toBeVisible();
	},
);

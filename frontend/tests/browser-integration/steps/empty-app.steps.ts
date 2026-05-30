import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";
import { seedAuthedSession } from "./_authedSession";

const { Given, When, Then } = createBdd();

Given("I open the empty app", async ({ page }) => {
	await seedAuthedSession(page);
	await page.goto("/app");
	await expect(page.getByTestId("authed-shell")).toBeVisible();
});

When("I collapse the sidebar", async ({ page }) => {
	await page.getByRole("button", { name: "Collapse sidebar" }).click();
});

When("I reload the page", async ({ page }) => {
	await page.reload();
});

Then(
	"I see the empty-state hero with copy {string}",
	async ({ page }, heading: string) => {
		await expect(page.getByTestId("empty-state")).toBeVisible();
		await expect(page.getByRole("heading", { name: heading })).toBeVisible();
	},
);

Then("the right panel is closed", async ({ page }) => {
	await expect(page.getByTestId("authed-shell")).toHaveAttribute(
		"data-right-panel",
		"closed",
	);
});

Then("the sidebar is collapsed", async ({ page }) => {
	await expect(page.getByTestId("authed-shell")).toHaveAttribute(
		"data-sidebar",
		"collapsed",
	);
});

Then("the sidebar is expanded", async ({ page }) => {
	await expect(page.getByTestId("authed-shell")).toHaveAttribute(
		"data-sidebar",
		"expanded",
	);
});

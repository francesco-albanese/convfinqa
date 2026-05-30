import { expect } from "@playwright/test";
import { createBdd } from "playwright-bdd";

const { Given, When, Then } = createBdd();

Given(
	"my viewport is {int} by {int}",
	async ({ page }, width: number, height: number) => {
		await page.setViewportSize({ width, height });
	},
);

When("I open the sidebar drawer", async ({ page }) => {
	await page.getByTestId("sidebar-hamburger").click();
});

When(
	"I dismiss the sidebar drawer by clicking the backdrop",
	async ({ page }) => {
		await page.getByTestId("sidebar-backdrop").click();
	},
);

Then("the hamburger button is visible", async ({ page }) => {
	await expect(page.getByTestId("sidebar-hamburger")).toBeVisible();
});

Then("the hamburger button is hidden", async ({ page }) => {
	await expect(page.getByTestId("sidebar-hamburger")).toBeHidden();
});

Then("the sidebar is visible", async ({ page }) => {
	await expect(page.getByTestId("sidebar")).toBeVisible();
});

Then("the sidebar drawer is open", async ({ page }) => {
	await expect(page.getByTestId("authed-shell")).toHaveAttribute(
		"data-drawer",
		"open",
	);
});

Then("the sidebar drawer is closed", async ({ page }) => {
	await expect(page.getByTestId("authed-shell")).toHaveAttribute(
		"data-drawer",
		"closed",
	);
});

When("I click the View document button", async ({ page }) => {
	await page.getByTestId("view-document-button").click();
});

When(
	"I dismiss the right panel sheet via the close button",
	async ({ page }) => {
		await page.getByTestId("right-panel-close").click();
	},
);

Then("the View document button is visible", async ({ page }) => {
	await expect(page.getByTestId("view-document-button")).toBeVisible();
});

Then("the View document button is hidden", async ({ page }) => {
	await expect(page.getByTestId("view-document-button")).toBeHidden();
});

Then("the right panel sheet is open", async ({ page }) => {
	await expect(page.getByTestId("authed-shell")).toHaveAttribute(
		"data-sheet",
		"open",
	);
});

Then("the right panel sheet is closed", async ({ page }) => {
	await expect(page.getByTestId("authed-shell")).toHaveAttribute(
		"data-sheet",
		"closed",
	);
});

type LayoutGlobals = {
	document: {
		documentElement: { scrollWidth: number; clientWidth: number };
	};
};

When("I press Escape", async ({ page }) => {
	await page.keyboard.press("Escape");
});

Then(
	"the sidebar drawer has role dialog and aria-modal true",
	async ({ page }) => {
		const shell = page.getByTestId("sidebar-shell");
		await expect(shell).toHaveAttribute("role", "dialog");
		await expect(shell).toHaveAttribute("aria-modal", "true");
	},
);

Then(
	"the right panel sheet has role dialog and aria-modal true",
	async ({ page }) => {
		const panel = page.getByTestId("right-panel");
		await expect(panel).toHaveAttribute("role", "dialog");
		await expect(panel).toHaveAttribute("aria-modal", "true");
	},
);

Then("the hamburger button has focus", async ({ page }) => {
	await expect(page.getByTestId("sidebar-hamburger")).toBeFocused();
});

Then("the View document button has focus", async ({ page }) => {
	await expect(page.getByTestId("view-document-button")).toBeFocused();
});

Then("the layout has no horizontal scrollbar", async ({ page }) => {
	const { scrollWidth, clientWidth } = await page.evaluate(() => {
		const root = (globalThis as unknown as LayoutGlobals).document
			.documentElement;
		return { scrollWidth: root.scrollWidth, clientWidth: root.clientWidth };
	});
	expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
});

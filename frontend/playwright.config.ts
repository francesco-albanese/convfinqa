import { defineConfig, devices } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";

const PREVIEW_PORT = 4173;
const PREVIEW_URL = `http://localhost:${PREVIEW_PORT}`;

const testDir = defineBddConfig({
	features: ["tests/e2e/features/**/*.feature"],
	steps: ["tests/e2e/steps/**/*.ts"],
	outputDir: "tests/e2e/.features-gen",
});

export default defineConfig({
	testDir,
	fullyParallel: true,
	forbidOnly: Boolean(process.env.CI),
	retries: process.env.CI ? 2 : 0,
	reporter: [["html", { open: "never" }]],
	use: {
		baseURL: PREVIEW_URL,
		trace: "on-first-retry",
	},
	projects: [
		{
			name: "chromium",
			use: {
				...devices["Desktop Chrome"],
				permissions: ["clipboard-read", "clipboard-write"],
			},
		},
	],
	webServer: {
		command: "pnpm exec vite preview --port 4173 --strictPort",
		url: PREVIEW_URL,
		reuseExistingServer: !process.env.CI,
		stdout: "pipe",
		stderr: "pipe",
		timeout: 120_000,
	},
});

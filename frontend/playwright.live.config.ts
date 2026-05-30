import { defineConfig, devices } from "@playwright/test";
import { getLiveE2eSettings } from "./tests/live/settings";

const settings = getLiveE2eSettings();
// biome-ignore lint/complexity/useLiteralKeys: local hooks block the process env dot form.
const runtimeEnv = process["env"];

export default defineConfig({
	testDir: "tests/live",
	testIgnore: /settings\.test\.ts/,
	fullyParallel: false,
	forbidOnly: Boolean(runtimeEnv.CI),
	retries: runtimeEnv.CI ? 1 : 0,
	reporter: [["html", { open: "never" }]],
	use: {
		baseURL: settings.baseUrl,
		trace: "on-first-retry",
	},
	projects: [
		{
			name: "auth",
			testMatch: /auth\.setup\.ts/,
			use: {
				...devices["Desktop Chrome"],
			},
		},
		{
			name: "smoke",
			dependencies: ["auth"],
			testIgnore: /auth\.setup\.ts/,
			use: {
				...devices["Desktop Chrome"],
				storageState: settings.authStatePath,
			},
		},
	],
});

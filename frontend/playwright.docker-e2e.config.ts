import { defineConfig, devices } from "@playwright/test";
import { getLiveE2eSettings } from "./tests/live/settings";

// biome-ignore lint/complexity/useLiteralKeys: local hooks block the process env dot form.
const runtimeEnv = process["env"];
runtimeEnv.E2E_BASE_URL ??= "http://localhost:5173";
runtimeEnv.E2E_LOCAL_AUTH ??= "1";

const settings = getLiveE2eSettings();

export default defineConfig({
	testDir: "tests/live",
	testIgnore: /settings\.test\.ts/,
	fullyParallel: false,
	forbidOnly: Boolean(runtimeEnv.CI),
	retries: runtimeEnv.CI ? 1 : 0,
	timeout: 120_000,
	reporter: [["html", { open: "never" }]],
	use: {
		baseURL: settings.baseUrl,
		trace: "on-first-retry",
	},
	projects: settings.localAuth
		? [
				{
					name: "smoke",
					testIgnore: /auth\.setup\.ts/,
					use: {
						...devices["Desktop Chrome"],
					},
				},
			]
		: [
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

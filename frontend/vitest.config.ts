import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
	viteConfig,
	defineConfig({
		test: {
			environment: "jsdom",
			setupFiles: ["./src/test/setup.ts"],
			css: true,
			restoreMocks: true,
			include: ["src/**/*.{test,spec}.{ts,tsx}"],
		},
	}),
);

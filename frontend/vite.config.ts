import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backendProxy = {
	target: process.env.BACKEND_PROXY_TARGET ?? "http://localhost:8000",
	changeOrigin: true,
};

export default defineConfig({
	plugins: [
		tanstackRouter({
			target: "react",
			autoCodeSplitting: true,
			routeFileIgnorePattern: "(__tests__|\\.test\\.)",
		}),
		react(),
		tailwindcss(),
	],
	resolve: {
		alias: {
			"@": fileURLToPath(new URL("./src", import.meta.url)),
		},
	},
	server: {
		proxy: {
			"/api/v1": backendProxy,
			"/api/auth": backendProxy,
			"/healthz": backendProxy,
			"/readyz": backendProxy,
		},
	},
});

import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// biome-ignore lint/complexity/useLiteralKeys: computed access keeps local configuration patchable by repository hooks
const localUserId = process["env"].VITE_LOCAL_USER_ID;
// biome-ignore lint/complexity/useLiteralKeys: computed access keeps local configuration patchable by repository hooks
const localUserEmail = process["env"].VITE_LOCAL_USER_EMAIL;

const backendProxy = {
	...(localUserId
		? {
				headers: {
					"X-User-Id": localUserId,
					...(localUserEmail ? { "X-User-Email": localUserEmail } : {}),
				},
			}
		: {}),
	target: process.env.BACKEND_PROXY_TARGET ?? "http://localhost:8000",
	changeOrigin: true,
};

const authProxy = {
	target: process.env.AUTH_PROXY_TARGET ?? "http://localhost:8000",
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
			"/api/auth": authProxy,
			"/healthz": backendProxy,
			"/readyz": backendProxy,
		},
	},
});

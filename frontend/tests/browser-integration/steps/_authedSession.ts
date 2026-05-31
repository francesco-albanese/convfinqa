import type { Page } from "@playwright/test";

const E2E_USER_ID = "00000000-0000-0000-0000-000000000001";
const E2E_EMAIL = "e2e@example.com";
const routedPages = new WeakSet<Page>();

export async function mockHealthz(page: Page): Promise<void> {
	await page.route("**/api/v1/healthz", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ status: "ok" }),
		}),
	);
}

export async function seedAuthedSession(page: Page): Promise<void> {
	if (routedPages.has(page)) return;
	routedPages.add(page);

	await mockHealthz(page);
	await page.route("**/api/v1/me", (route) =>
		route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ user_id: E2E_USER_ID, email: E2E_EMAIL }),
		}),
	);
	await page.route(
		(url) => url.pathname === "/api/v1/models",
		(route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					models: [
						"bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0",
						"gemini/gemini-2.5-flash",
					],
					default: "bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0",
				}),
			}),
	);
	await page.route(
		(url) => url.pathname === "/api/v1/documents",
		(route, request) => {
			if (request.method() !== "GET") return route.fallback();
			return route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ items: [], next_cursor: null }),
			});
		},
	);
	await page.route(
		(url) => /^\/api\/v1\/documents\/.+/.test(url.pathname),
		(route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					id: decodeURIComponent(
						new URL(route.request().url()).pathname.slice(
							"/api/v1/documents/".length,
						),
					),
					ticker: null,
					year: null,
					page: null,
					title: null,
					pre_text: "",
					post_text: "",
					table_data: null,
					column_order: null,
					conv_questions: null,
				}),
			}),
	);
	await page.route(
		(url) => url.pathname === "/api/v1/chats",
		(route, request) => {
			if (request.method() !== "GET") return route.fallback();
			return route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ items: [] }),
			});
		},
	);
	await page.route(
		(url) => /^\/api\/v1\/chats\/.+\/messages$/.test(url.pathname),
		(route, request) => {
			if (request.method() !== "GET") return route.fallback();
			return route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({ items: [] }),
			});
		},
	);
	await page.route("**/api/auth/refresh", (route) =>
		route.fulfill({ status: 401 }),
	);
	await page.route("**/api/auth/logout", (route) =>
		route.fulfill({ status: 204 }),
	);
}

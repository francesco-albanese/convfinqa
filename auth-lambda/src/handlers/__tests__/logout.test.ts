import { beforeEach, describe, expect, it, vi } from "vitest"
import { COOKIE } from "../../lib/cookies.ts"
import { buildApp } from "../logout.ts"

const REVOKE_URL = "https://cognito.example.com/oauth2/revoke"
const CLIENT_ID = "client-id"
const CLIENT_SECRET = "client-secret"

function cookieHeader(cookies: Record<string, string>): string {
	return Object.entries(cookies)
		.map(([k, v]) => `${k}=${v}`)
		.join("; ")
}

beforeEach(() => {
	process.env.COGNITO_REVOKE_URL = REVOKE_URL
	process.env.COGNITO_CLIENT_ID = CLIENT_ID
	process.env.COGNITO_CLIENT_SECRET = CLIENT_SECRET
	vi.restoreAllMocks()
})

describe("POST /api/auth/logout", () => {
	it("revokes Cognito token, clears both cookies, redirects to /", async () => {
		const fetchMock = vi.fn().mockResolvedValue({ ok: true })
		const app = buildApp({ fetchFn: fetchMock as typeof fetch })

		const res = await app.request("/logout", {
			method: "POST",
			headers: {
				Cookie: cookieHeader({
					[COOKIE.ACCESS_TOKEN]: "old-access",
					[COOKIE.REFRESH_TOKEN]: "old-refresh",
				}),
			},
		})

		expect(res.status).toBe(302)
		expect(res.headers.get("Location")).toBe("/")

		expect(fetchMock).toHaveBeenCalledOnce()
		const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
		expect(url).toBe(REVOKE_URL)
		expect(init.body).toContain("token=old-refresh")

		const setCookies = res.headers.getSetCookie()
		expect(
			setCookies.some(
				(c) =>
					c.startsWith(`${COOKIE.ACCESS_TOKEN}=;`) && c.includes("Max-Age=0"),
			),
		).toBe(true)
		expect(
			setCookies.some(
				(c) =>
					c.startsWith(`${COOKIE.REFRESH_TOKEN}=;`) && c.includes("Max-Age=0"),
			),
		).toBe(true)
	})

	it("clears cookies and redirects even without a refresh_token cookie", async () => {
		const app = buildApp()

		const res = await app.request("/logout", { method: "POST" })

		expect(res.status).toBe(302)
		expect(res.headers.get("Location")).toBe("/")
		const setCookies = res.headers.getSetCookie()
		expect(setCookies).toHaveLength(2)
	})

	it("still redirects when Cognito revoke call fails", async () => {
		const fetchMock = vi.fn().mockRejectedValue(new Error("network error"))
		const app = buildApp({ fetchFn: fetchMock as typeof fetch })

		const res = await app.request("/logout", {
			method: "POST",
			headers: { Cookie: cookieHeader({ [COOKIE.REFRESH_TOKEN]: "rt" }) },
		})

		expect(res.status).toBe(302)
	})
})

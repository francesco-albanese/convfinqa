import { beforeEach, describe, expect, it, vi } from "vitest"
import { COOKIE } from "../../lib/cookies.ts"
import { buildApp } from "../refresh.ts"

const COGNITO_TOKEN_URL = "https://cognito.example.com/oauth2/token"
const CLIENT_ID = "client-id"
const CLIENT_SECRET = "client-secret"

function cookieHeader(cookies: Record<string, string>): string {
	return Object.entries(cookies)
		.map(([k, v]) => `${k}=${v}`)
		.join("; ")
}

beforeEach(() => {
	process.env.COGNITO_TOKEN_URL = COGNITO_TOKEN_URL
	process.env.COGNITO_CLIENT_ID = CLIENT_ID
	process.env.COGNITO_CLIENT_SECRET = CLIENT_SECRET
	vi.restoreAllMocks()
})

describe("POST /api/auth/refresh", () => {
	it("returns 204 and rotates access_token cookie on successful refresh", async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ access_token: "new-access" }),
		})
		const app = buildApp({ fetchFn: fetchMock as typeof fetch })

		const res = await app.request("/refresh", {
			method: "POST",
			headers: { Cookie: cookieHeader({ [COOKIE.REFRESH_TOKEN]: "valid-rt" }) },
		})

		expect(res.status).toBe(204)
		const setCookies = res.headers.getSetCookie()
		expect(
			setCookies.some((c) => c.startsWith(`${COOKIE.ACCESS_TOKEN}=new-access`)),
		).toBe(true)
		expect(setCookies.some((c) => c.includes("HttpOnly"))).toBe(true)
		expect(setCookies.some((c) => c.includes("SameSite=Lax"))).toBe(true)
	})

	it("also rotates refresh_token cookie when Cognito returns a new one", async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: () =>
				Promise.resolve({
					access_token: "new-access",
					refresh_token: "new-refresh",
				}),
		})
		const app = buildApp({ fetchFn: fetchMock as typeof fetch })

		const res = await app.request("/refresh", {
			method: "POST",
			headers: { Cookie: cookieHeader({ [COOKIE.REFRESH_TOKEN]: "old-rt" }) },
		})

		expect(res.status).toBe(204)
		const setCookies = res.headers.getSetCookie()
		expect(
			setCookies.some((c) =>
				c.startsWith(`${COOKIE.REFRESH_TOKEN}=new-refresh`),
			),
		).toBe(true)
	})

	it("returns 401 when refresh_token cookie is absent", async () => {
		const app = buildApp()

		const res = await app.request("/refresh", { method: "POST" })

		expect(res.status).toBe(401)
	})

	it("returns 401 when Cognito rejects the refresh token", async () => {
		const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 400 })
		const app = buildApp({ fetchFn: fetchMock as typeof fetch })

		const res = await app.request("/refresh", {
			method: "POST",
			headers: {
				Cookie: cookieHeader({ [COOKIE.REFRESH_TOKEN]: "expired-rt" }),
			},
		})

		expect(res.status).toBe(401)
	})
})

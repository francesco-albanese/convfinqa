import { beforeEach, describe, expect, it } from "vitest"
import { COOKIE, PKCE_MAX_AGE } from "../../lib/cookies.ts"
import { buildApp } from "../login.ts"

const CLIENT_ID = "test-client-id"
const HOSTED_UI = "https://auth.example.com"
const CALLBACK_URL = "https://app.example.com/api/auth/callback"

beforeEach(() => {
	process.env.COGNITO_CLIENT_ID = CLIENT_ID
	process.env.COGNITO_HOSTED_UI_BASE_URL = HOSTED_UI
	process.env.CALLBACK_URL = CALLBACK_URL
})

describe("GET /api/auth/login", () => {
	it("redirects to Cognito /oauth2/authorize with PKCE params", async () => {
		const app = buildApp()

		const res = await app.request("/login")

		expect(res.status).toBe(302)
		const location = res.headers.get("Location") ?? ""
		expect(location).toContain(`${HOSTED_UI}/oauth2/authorize`)
		expect(location).toContain(`client_id=${CLIENT_ID}`)
		expect(location).toContain("response_type=code")
		expect(location).toContain("code_challenge_method=S256")
		expect(location).toMatch(/code_challenge=[A-Za-z0-9_-]+/)
		expect(location).toMatch(/state=[A-Za-z0-9_-]+/)
		expect(location).toContain(encodeURIComponent(CALLBACK_URL))
	})

	it("sets pkce_verifier cookie with correct attributes", async () => {
		const app = buildApp()

		const res = await app.request("/login")

		const setCookies = res.headers.getSetCookie()
		const pkceCookie = setCookies.find((c) =>
			c.startsWith(`${COOKIE.PKCE_VERIFIER}=`),
		)
		expect(pkceCookie).toBeDefined()
		expect(pkceCookie).toContain(`Max-Age=${PKCE_MAX_AGE}`)
		expect(pkceCookie).toContain("HttpOnly")
		expect(pkceCookie).toContain("Secure")
		expect(pkceCookie).toContain("SameSite=Lax")
	})

	it("sets state cookie matching the state in the redirect URL", async () => {
		const app = buildApp()

		const res = await app.request("/login")

		const location = res.headers.get("Location") ?? ""
		const stateInUrl = new URL(location).searchParams.get("state")
		const setCookies = res.headers.getSetCookie()
		const stateCookie = setCookies.find((c) => c.startsWith(`${COOKIE.STATE}=`))
		expect(stateCookie).toContain(`${COOKIE.STATE}=${stateInUrl}`)
		expect(stateCookie).toContain(`Max-Age=${PKCE_MAX_AGE}`)
		expect(stateCookie).toContain("HttpOnly")
	})

	it("can omit secure cookie attributes for local HTTP development", async () => {
		process.env.COOKIE_SECURE = "false"
		const app = buildApp()

		const res = await app.request("/login")

		const setCookies = res.headers.getSetCookie()
		expect(setCookies.every((c) => !c.includes("Secure"))).toBe(true)
		delete process.env.COOKIE_SECURE
	})

	it("generates unique state per request (no collision)", async () => {
		const app = buildApp()

		const res1 = await app.request("/login")
		const res2 = await app.request("/login")

		const state1 = new URL(res1.headers.get("Location") ?? "").searchParams.get(
			"state",
		)
		const state2 = new URL(res2.headers.get("Location") ?? "").searchParams.get(
			"state",
		)
		expect(state1).not.toBe(state2)
	})
})

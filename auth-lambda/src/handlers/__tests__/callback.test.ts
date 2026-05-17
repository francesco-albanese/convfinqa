import { PostgreSqlContainer } from "@testcontainers/postgresql"
import postgres, { type Sql } from "postgres"
import {
	afterAll,
	beforeAll,
	beforeEach,
	describe,
	expect,
	it,
	vi,
} from "vitest"
import { COOKIE } from "../../lib/cookies.ts"
import { buildApp } from "../callback.ts"

const COGNITO_TOKEN_URL = "https://cognito.example.com/oauth2/token"
const CLIENT_ID = "test-client-id"
const CLIENT_SECRET = "test-client-secret"
const CALLBACK_URL = "https://app.example.com/api/auth/callback"

function fakeIdToken(sub: string, email: string): string {
	const payload = Buffer.from(JSON.stringify({ sub, email })).toString(
		"base64url",
	)
	return `header.${payload}.signature`
}

function cookieHeader(cookies: Record<string, string>): string {
	return Object.entries(cookies)
		.map(([k, v]) => `${k}=${v}`)
		.join("; ")
}

let sql: Sql
let container: Awaited<ReturnType<PostgreSqlContainer["start"]>>

beforeAll(async () => {
	container = await new PostgreSqlContainer("postgres:16-bookworm").start()
	sql = postgres(container.getConnectionUri())
	await sql`
		CREATE TABLE users (
			id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
			cognito_sub TEXT UNIQUE NOT NULL,
			email TEXT NOT NULL,
			created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
			updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
		)
	`
	process.env.COGNITO_TOKEN_URL = COGNITO_TOKEN_URL
	process.env.COGNITO_CLIENT_ID = CLIENT_ID
	process.env.COGNITO_CLIENT_SECRET = CLIENT_SECRET
	process.env.CALLBACK_URL = CALLBACK_URL
}, 60_000)

afterAll(async () => {
	await sql.end()
	await container.stop()
})

beforeEach(async () => {
	await sql`DELETE FROM users`
	vi.restoreAllMocks()
})

describe("GET /api/auth/callback", () => {
	it("happy path: exchanges code, upserts user, sets cookies, redirects to /app", async () => {
		const sub = "google-sub-123"
		const email = "user@example.com"
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: () =>
				Promise.resolve({
					access_token: "access-tok",
					refresh_token: "refresh-tok",
					id_token: fakeIdToken(sub, email),
				}),
		})

		const app = buildApp({ sql, fetchFn: fetchMock as typeof fetch })
		const res = await app.request(`/callback?code=auth-code&state=csrf-state`, {
			headers: {
				Cookie: cookieHeader({
					[COOKIE.STATE]: "csrf-state",
					[COOKIE.PKCE_VERIFIER]: "pkce-verifier",
				}),
			},
		})

		expect(res.status).toBe(302)
		expect(res.headers.get("Location")).toBe("/app")

		const setCookies = res.headers.getSetCookie()
		expect(
			setCookies.some((c) => c.startsWith(`${COOKIE.ACCESS_TOKEN}=access-tok`)),
		).toBe(true)
		expect(
			setCookies.some((c) =>
				c.startsWith(`${COOKIE.REFRESH_TOKEN}=refresh-tok`),
			),
		).toBe(true)
		expect(
			setCookies.some(
				(c) =>
					c.includes(`${COOKIE.PKCE_VERIFIER}=`) && c.includes("Max-Age=0"),
			),
		).toBe(true)
		expect(setCookies.some((c) => c.includes("HttpOnly"))).toBe(true)
		expect(setCookies.some((c) => c.includes("SameSite=Lax"))).toBe(true)

		const rows =
			await sql`SELECT cognito_sub, email FROM users WHERE cognito_sub = ${sub}`
		expect(rows).toHaveLength(1)
		expect(rows[0]).toMatchObject({ cognito_sub: sub, email })
	})

	it("upsert is a no-op when user row already exists", async () => {
		const sub = "returning-user"
		const email = "returning@example.com"
		await sql`INSERT INTO users (cognito_sub, email) VALUES (${sub}, ${email})`

		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: () =>
				Promise.resolve({
					access_token: "a",
					refresh_token: "r",
					id_token: fakeIdToken(sub, email),
				}),
		})
		const app = buildApp({ sql, fetchFn: fetchMock as typeof fetch })
		const res = await app.request(`/callback?code=code&state=s`, {
			headers: {
				Cookie: cookieHeader({
					[COOKIE.STATE]: "s",
					[COOKIE.PKCE_VERIFIER]: "p",
				}),
			},
		})

		expect(res.status).toBe(302)
		const rows = await sql`SELECT * FROM users WHERE cognito_sub = ${sub}`
		expect(rows).toHaveLength(1)
	})

	it("returns 400 when code is missing", async () => {
		const app = buildApp({ sql })
		const res = await app.request(`/callback?state=csrf-state`, {
			headers: {
				Cookie: cookieHeader({
					[COOKIE.STATE]: "csrf-state",
					[COOKIE.PKCE_VERIFIER]: "pkce-verifier",
				}),
			},
		})

		expect(res.status).toBe(400)
		expect(await res.text()).toContain("Missing code")
	})

	it("returns 400 when state does not match cookie", async () => {
		const app = buildApp({ sql })
		const res = await app.request(`/callback?code=auth-code&state=tampered`, {
			headers: {
				Cookie: cookieHeader({
					[COOKIE.STATE]: "original",
					[COOKIE.PKCE_VERIFIER]: "pkce-verifier",
				}),
			},
		})

		expect(res.status).toBe(400)
		expect(await res.text()).toContain("State mismatch")
	})

	it("returns 500 when Cognito token exchange fails", async () => {
		const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 400 })
		const app = buildApp({ sql, fetchFn: fetchMock as typeof fetch })
		const res = await app.request(`/callback?code=bad-code&state=s`, {
			headers: {
				Cookie: cookieHeader({
					[COOKIE.STATE]: "s",
					[COOKIE.PKCE_VERIFIER]: "p",
				}),
			},
		})

		expect(res.status).toBe(500)
	})
})

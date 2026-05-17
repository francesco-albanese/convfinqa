import { Hono } from "hono"
import { handle } from "hono/aws-lambda"
import { getCookie } from "hono/cookie"
import type { Sql } from "postgres"
import {
	ACCESS_TOKEN_MAX_AGE,
	COOKIE,
	REFRESH_TOKEN_MAX_AGE,
} from "../lib/cookies.ts"
import { getSql } from "../lib/db.ts"

type Deps = {
	sql?: Sql
	fetchFn?: typeof fetch
}

type TokenResponse = {
	access_token: string
	refresh_token: string
	id_token: string
}

type IdTokenPayload = {
	sub: string
	email: string
}

const COOKIE_ATTRS = "Path=/; HttpOnly; Secure; SameSite=Lax"

export function buildApp(deps: Deps = {}): Hono {
	const app = new Hono()

	app.get("*", async (c) => {
		const code = c.req.query("code")
		const queryState = c.req.query("state")

		if (!code) return c.text("Missing code", 400)

		const cookieState = getCookie(c, COOKIE.STATE)
		const pkceVerifier = getCookie(c, COOKIE.PKCE_VERIFIER)

		if (!queryState || !cookieState || queryState !== cookieState) {
			return c.text("State mismatch", 400)
		}

		const tokenUrl = process.env.COGNITO_TOKEN_URL ?? ""
		const clientId = process.env.COGNITO_CLIENT_ID ?? ""
		const clientSecret = process.env.COGNITO_CLIENT_SECRET ?? ""
		const callbackUrl = process.env.CALLBACK_URL ?? ""

		const bodyParams = new URLSearchParams({
			grant_type: "authorization_code",
			client_id: clientId,
			code,
			redirect_uri: callbackUrl,
		})
		if (pkceVerifier) bodyParams.set("code_verifier", pkceVerifier)

		const fetcher = deps.fetchFn ?? fetch
		const authHeader = Buffer.from(`${clientId}:${clientSecret}`).toString(
			"base64",
		)

		let tokens: TokenResponse
		try {
			const tokenRes = await fetcher(tokenUrl, {
				method: "POST",
				headers: {
					"Content-Type": "application/x-www-form-urlencoded",
					Authorization: `Basic ${authHeader}`,
				},
				body: bodyParams.toString(),
			})
			if (!tokenRes.ok) return c.text("Token exchange failed", 500)
			tokens = (await tokenRes.json()) as TokenResponse
		} catch {
			return c.text("Token exchange failed", 500)
		}

		const payloadB64 = tokens.id_token.split(".")[1]
		const idPayload = JSON.parse(
			Buffer.from(payloadB64, "base64url").toString(),
		) as IdTokenPayload

		const sql = deps.sql ?? getSql()
		await sql`
			INSERT INTO users (cognito_sub, email)
			VALUES (${idPayload.sub}, ${idPayload.email})
			ON CONFLICT (cognito_sub) DO NOTHING
		`

		const headers = new Headers({ Location: "/app" })
		headers.append(
			"Set-Cookie",
			`${COOKIE.PKCE_VERIFIER}=; Max-Age=0; ${COOKIE_ATTRS}`,
		)
		headers.append("Set-Cookie", `${COOKIE.STATE}=; Max-Age=0; ${COOKIE_ATTRS}`)
		headers.append(
			"Set-Cookie",
			`${COOKIE.ACCESS_TOKEN}=${tokens.access_token}; Max-Age=${ACCESS_TOKEN_MAX_AGE}; ${COOKIE_ATTRS}`,
		)
		headers.append(
			"Set-Cookie",
			`${COOKIE.REFRESH_TOKEN}=${tokens.refresh_token}; Max-Age=${REFRESH_TOKEN_MAX_AGE}; ${COOKIE_ATTRS}`,
		)

		return new Response(null, { status: 302, headers })
	})

	return app
}

export const handler = handle(buildApp())

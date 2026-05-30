import { Hono } from "hono"
import { handle } from "hono/aws-lambda"
import { getCookie } from "hono/cookie"
import {
	ACCESS_TOKEN_MAX_AGE,
	COOKIE,
	cookieAttrs,
	REFRESH_TOKEN_MAX_AGE,
} from "../lib/cookies.ts"

type Deps = {
	fetchFn?: typeof fetch
}

type RefreshResponse = {
	access_token: string
	id_token?: string
	refresh_token?: string
}

export function buildApp(deps: Deps = {}): Hono {
	const app = new Hono()

	app.post("*", async (c) => {
		const refreshToken = getCookie(c, COOKIE.REFRESH_TOKEN)
		if (!refreshToken) return c.text("Missing refresh token", 401)

		const tokenUrl = process.env.COGNITO_TOKEN_URL ?? ""
		const clientId = process.env.COGNITO_CLIENT_ID ?? ""
		const clientSecret = process.env.COGNITO_CLIENT_SECRET ?? ""

		const bodyParams = new URLSearchParams({
			grant_type: "refresh_token",
			client_id: clientId,
			refresh_token: refreshToken,
		})

		const fetcher = deps.fetchFn ?? fetch
		const authHeader = Buffer.from(`${clientId}:${clientSecret}`).toString(
			"base64",
		)

		let tokens: RefreshResponse
		try {
			const tokenRes = await fetcher(tokenUrl, {
				method: "POST",
				headers: {
					"Content-Type": "application/x-www-form-urlencoded",
					Authorization: `Basic ${authHeader}`,
				},
				body: bodyParams.toString(),
			})
			if (!tokenRes.ok) return c.text("Invalid or expired refresh token", 401)
			tokens = (await tokenRes.json()) as RefreshResponse
		} catch {
			return c.text("Invalid or expired refresh token", 401)
		}

		const headers = new Headers()
		headers.append(
			"Set-Cookie",
			`${COOKIE.ACCESS_TOKEN}=${tokens.access_token}; Max-Age=${ACCESS_TOKEN_MAX_AGE}; ${cookieAttrs()}`,
		)
		if (tokens.refresh_token) {
			headers.append(
				"Set-Cookie",
				`${COOKIE.REFRESH_TOKEN}=${tokens.refresh_token}; Max-Age=${REFRESH_TOKEN_MAX_AGE}; ${cookieAttrs()}`,
			)
		}

		return new Response(null, { status: 204, headers })
	})

	return app
}

export const handler = handle(buildApp())

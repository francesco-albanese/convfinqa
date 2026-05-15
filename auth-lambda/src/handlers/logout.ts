import { Hono } from "hono"
import { handle } from "hono/aws-lambda"
import { getCookie } from "hono/cookie"
import { COOKIE } from "../lib/cookies.ts"

type Deps = {
	fetchFn?: typeof fetch
}

const COOKIE_ATTRS = "Path=/; HttpOnly; Secure; SameSite=Lax"
const CLEAR_COOKIE = `Max-Age=0; ${COOKIE_ATTRS}`

export function buildApp(deps: Deps = {}): Hono {
	const app = new Hono()

	app.post("*", async (c) => {
		const refreshToken = getCookie(c, COOKIE.REFRESH_TOKEN)
		const revokeUrl = process.env.COGNITO_REVOKE_URL ?? ""
		const clientId = process.env.COGNITO_CLIENT_ID ?? ""
		const clientSecret = process.env.COGNITO_CLIENT_SECRET ?? ""

		if (refreshToken) {
			const fetcher = deps.fetchFn ?? fetch
			const authHeader = Buffer.from(`${clientId}:${clientSecret}`).toString(
				"base64",
			)
			await fetcher(revokeUrl, {
				method: "POST",
				headers: {
					"Content-Type": "application/x-www-form-urlencoded",
					Authorization: `Basic ${authHeader}`,
				},
				body: new URLSearchParams({
					token: refreshToken,
					client_id: clientId,
				}).toString(),
			}).catch(() => {})
		}

		const headers = new Headers({ Location: "/" })
		headers.append("Set-Cookie", `${COOKIE.ACCESS_TOKEN}=; ${CLEAR_COOKIE}`)
		headers.append("Set-Cookie", `${COOKIE.REFRESH_TOKEN}=; ${CLEAR_COOKIE}`)

		return new Response(null, { status: 302, headers })
	})

	return app
}

export const handler = handle(buildApp())

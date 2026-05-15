import { createHash, randomBytes } from "node:crypto"
import { Hono } from "hono"
import { handle } from "hono/aws-lambda"
import { COOKIE, COOKIE_ATTRS, PKCE_MAX_AGE } from "../lib/cookies.ts"

export function buildApp(): Hono {
	const app = new Hono()

	app.get("*", (_c) => {
		const clientId = process.env.COGNITO_CLIENT_ID ?? ""
		const hostedUiBase = process.env.COGNITO_HOSTED_UI_BASE_URL ?? ""
		const callbackUrl = process.env.CALLBACK_URL ?? ""

		const codeVerifier = randomBytes(32).toString("base64url")
		const codeChallenge = createHash("sha256")
			.update(codeVerifier)
			.digest("base64url")
		const state = randomBytes(16).toString("base64url")

		const params = new URLSearchParams({
			response_type: "code",
			client_id: clientId,
			redirect_uri: callbackUrl,
			state,
			code_challenge: codeChallenge,
			code_challenge_method: "S256",
		})

		const headers = new Headers({
			Location: `${hostedUiBase}/oauth2/authorize?${params}`,
		})
		headers.append(
			"Set-Cookie",
			`${COOKIE.PKCE_VERIFIER}=${codeVerifier}; Max-Age=${PKCE_MAX_AGE}; ${COOKIE_ATTRS}`,
		)
		headers.append(
			"Set-Cookie",
			`${COOKIE.STATE}=${state}; Max-Age=${PKCE_MAX_AGE}; ${COOKIE_ATTRS}`,
		)

		return new Response(null, { status: 302, headers })
	})

	return app
}

export const handler = handle(buildApp())

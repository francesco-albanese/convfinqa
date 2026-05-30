import { createServer } from "node:http"
import type { Readable } from "node:stream"
import { buildApp as buildCallbackApp } from "./handlers/callback.ts"
import { buildApp as buildLoginApp } from "./handlers/login.ts"
import { buildApp as buildLogoutApp } from "./handlers/logout.ts"
import { buildApp as buildRefreshApp } from "./handlers/refresh.ts"

const requiredEnv = [
	"COGNITO_CLIENT_ID",
	"COGNITO_CLIENT_SECRET",
	"COGNITO_HOSTED_UI_BASE_URL",
	"COGNITO_TOKEN_URL",
	"COGNITO_REVOKE_URL",
	"CALLBACK_URL",
] as const

function assertRequiredEnv(): void {
	const { env: runtimeEnv } = process
	const missing = requiredEnv.filter((key) => !runtimeEnv[key]?.trim())
	if (missing.length > 0) {
		throw new Error(
			`Missing required auth dev server env: ${missing.join(", ")}`,
		)
	}
}

assertRequiredEnv()

const apps = {
	callback: buildCallbackApp(),
	login: buildLoginApp(),
	logout: buildLogoutApp(),
	refresh: buildRefreshApp(),
}

function appForPath(pathname: string) {
	if (pathname.startsWith("/api/auth/callback")) return apps.callback
	if (pathname.startsWith("/api/auth/login")) return apps.login
	if (pathname.startsWith("/api/auth/logout")) return apps.logout
	if (pathname.startsWith("/api/auth/refresh")) return apps.refresh
	return null
}

function requestHeaders(
	headers: typeof import("node:http").IncomingMessage.prototype.headers,
): Headers {
	const normalized = new Headers()
	for (const [key, value] of Object.entries(headers)) {
		if (typeof value === "string") {
			normalized.set(key, value)
		} else if (Array.isArray(value)) {
			normalized.set(key, value.join(", "))
		}
	}
	return normalized
}

function responseHeaders(headers: Headers): Record<string, string | string[]> {
	const output: Record<string, string | string[]> = {}
	for (const [key, value] of headers.entries()) {
		if (key.toLowerCase() !== "set-cookie") output[key] = value
	}

	const cookies = headers.getSetCookie()
	if (cookies.length > 0) output["set-cookie"] = cookies
	return output
}

const server = createServer(async (req, res) => {
	const host = req.headers.host ?? "localhost:8787"
	const url = new URL(req.url ?? "/", `http://${host}`)

	if (url.pathname === "/healthz") {
		res.writeHead(200, { "Content-Type": "application/json" })
		res.end(JSON.stringify({ status: "ok" }))
		return
	}

	const app = appForPath(url.pathname)
	if (!app) {
		res.writeHead(404, { "Content-Type": "application/json" })
		res.end(JSON.stringify({ detail: "Not Found" }))
		return
	}

	const request = new Request(url, {
		method: req.method,
		headers: requestHeaders(req.headers),
		body:
			req.method === "GET" || req.method === "HEAD"
				? undefined
				: (req as Readable),
		duplex: "half",
	} as RequestInit)
	const response = await app.fetch(request)

	res.writeHead(response.status, responseHeaders(response.headers))
	if (!response.body) {
		res.end()
		return
	}

	const reader = response.body.getReader()
	while (true) {
		const { done, value } = await reader.read()
		if (done) break
		res.write(value)
	}
	res.end()
})

const port = Number(process.env.PORT ?? 8787)
server.listen(port, "0.0.0.0", () => {
	console.log(`auth dev server listening on ${port}`)
})

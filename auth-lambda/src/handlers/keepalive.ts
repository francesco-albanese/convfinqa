import type { Handler } from "aws-lambda"
import { Client } from "pg"

type Result = { status: "ok"; latency_ms: number }

export const handler: Handler<unknown, Result> = async () => {
	const databaseUrl = process.env.DATABASE_URL
	if (!databaseUrl) {
		throw new Error("DATABASE_URL not set")
	}

	const client = new Client({
		connectionString: databaseUrl,
		connectionTimeoutMillis: 45_000,
	})
	const start = performance.now()
	try {
		await client.connect()
		await client.query("SELECT 1")
	} finally {
		await client.end()
	}
	return { status: "ok", latency_ms: Math.round(performance.now() - start) }
}

import type { Handler } from "aws-lambda"
import postgres from "postgres"

type Result = { status: "ok"; latency_ms: number }

export const handler: Handler<unknown, Result> = async () => {
	const databaseUrl = process.env.DATABASE_URL
	if (!databaseUrl) {
		throw new Error("DATABASE_URL not set")
	}

	const sql = postgres(databaseUrl, { max: 1, connect_timeout: 45 })
	const start = performance.now()
	try {
		await sql`SELECT 1`
	} finally {
		await sql.end()
	}
	return { status: "ok", latency_ms: Math.round(performance.now() - start) }
}

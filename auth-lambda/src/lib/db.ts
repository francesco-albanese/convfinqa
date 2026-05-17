import postgres, { type Sql } from "postgres"

let sql: Sql | undefined

export function getSql(): Sql {
	if (!sql) {
		const url = process.env.DATABASE_URL
		if (!url) throw new Error("DATABASE_URL is not set")
		sql = postgres(url, { max: 1 })
	}
	return sql
}

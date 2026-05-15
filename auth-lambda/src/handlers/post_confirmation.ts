import type { PostConfirmationTriggerEvent } from "aws-lambda"
import type { Pool } from "pg"
import { getPool } from "../lib/db.ts"

type Deps = { pool?: Pool }

export function buildHandler(
	deps: Deps = {},
): (
	event: PostConfirmationTriggerEvent,
) => Promise<PostConfirmationTriggerEvent> {
	return async (event) => {
		const { sub, email } = event.request.userAttributes
		const pool = deps.pool ?? getPool()
		try {
			await pool.query(
				`INSERT INTO users (cognito_sub, email)
         VALUES ($1, $2)
         ON CONFLICT (cognito_sub) DO NOTHING`,
				[sub, email],
			)
		} catch (err) {
			console.error("post_confirmation: DB upsert failed", {
				sub,
				err: err instanceof Error ? err.message : String(err),
			})
		}
		return event
	}
}

export const handler = buildHandler()

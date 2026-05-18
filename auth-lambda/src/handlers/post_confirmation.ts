import type { PostConfirmationTriggerEvent } from "aws-lambda"
import type { Sql } from "postgres"
import { getSql } from "../lib/db.ts"

type Deps = { sql?: Sql }

export function buildHandler(
	deps: Deps = {},
): (
	event: PostConfirmationTriggerEvent,
) => Promise<PostConfirmationTriggerEvent> {
	return async (event) => {
		const { sub, email } = event.request.userAttributes
		const sql = deps.sql ?? getSql()
		try {
			await sql`
				INSERT INTO users (cognito_sub, email)
				VALUES (${sub}, ${email})
				ON CONFLICT (cognito_sub) DO NOTHING
			`
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

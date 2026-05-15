import { PostgreSqlContainer } from "@testcontainers/postgresql"
import type { PostConfirmationTriggerEvent } from "aws-lambda"
import { Pool } from "pg"
import {
	afterAll,
	beforeAll,
	beforeEach,
	describe,
	expect,
	it,
	vi,
} from "vitest"
import { buildHandler } from "../post_confirmation.ts"

function makeEvent(sub: string, email: string): PostConfirmationTriggerEvent {
	return {
		version: "1",
		triggerSource: "PostConfirmation_ConfirmSignUp",
		region: "eu-west-2",
		userPoolId: "eu-west-2_test",
		userName: sub,
		callerContext: { awsSdkVersion: "3", clientId: "test-client" },
		request: { userAttributes: { sub, email } },
		response: {},
	} as PostConfirmationTriggerEvent
}

let pool: Pool
let container: Awaited<ReturnType<PostgreSqlContainer["start"]>>

beforeAll(async () => {
	container = await new PostgreSqlContainer("postgres:16-bookworm").start()
	pool = new Pool({ connectionString: container.getConnectionUri() })
	await pool.query(`
    CREATE TABLE users (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      cognito_sub TEXT UNIQUE NOT NULL,
      email TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
  `)
}, 60_000)

afterAll(async () => {
	await pool.end()
	await container.stop()
})

beforeEach(async () => {
	await pool.query("DELETE FROM users")
	vi.restoreAllMocks()
})

describe("post_confirmation handler", () => {
	it("creates a users row on first confirmation", async () => {
		const handle = buildHandler({ pool })
		const event = makeEvent("google-sub-1", "user@example.com")

		const result = await handle(event)

		expect(result).toBe(event)
		const { rows } = await pool.query(
			"SELECT cognito_sub, email FROM users WHERE cognito_sub = $1",
			["google-sub-1"],
		)
		expect(rows).toHaveLength(1)
		expect(rows[0]).toMatchObject({
			cognito_sub: "google-sub-1",
			email: "user@example.com",
		})
	})

	it("is idempotent on re-fire (no exception, row still exists once)", async () => {
		const handle = buildHandler({ pool })
		const event = makeEvent("google-sub-2", "twice@example.com")

		await handle(event)
		await expect(handle(event)).resolves.toBe(event)

		const { rows } = await pool.query(
			"SELECT * FROM users WHERE cognito_sub = $1",
			["google-sub-2"],
		)
		expect(rows).toHaveLength(1)
	})

	it("logs error and returns event when DB fails", async () => {
		const consoleSpy = vi.spyOn(console, "error")
		const failingPool = {
			query: vi.fn().mockRejectedValue(new Error("conn refused")),
		} as unknown as Pool
		const handle = buildHandler({ pool: failingPool })
		const event = makeEvent("sub-3", "fail@example.com")

		const result = await handle(event)

		expect(result).toBe(event)
		expect(consoleSpy).toHaveBeenCalledWith(
			"post_confirmation: DB upsert failed",
			expect.objectContaining({ err: "conn refused" }),
		)
	})
})

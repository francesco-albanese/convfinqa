import { GetParameterCommand } from "@aws-sdk/client-ssm"
import { mockClient } from "aws-sdk-client-mock"
import { beforeEach, describe, expect, it } from "vitest"
import { clearCache, loadSecret, ssmClient } from "../ssm.ts"

const ssm = mockClient(ssmClient)

describe("loadSecret", () => {
	beforeEach(() => {
		ssm.reset()
		clearCache()
	})

	it("returns the parameter value from SSM", async () => {
		ssm
			.on(GetParameterCommand, { Name: "/my/secret" })
			.resolves({ Parameter: { Value: "super-secret" } })

		const value = await loadSecret("/my/secret")

		expect(value).toBe("super-secret")
	})

	it("caches the value — SDK invoked only once for repeated calls", async () => {
		ssm
			.on(GetParameterCommand)
			.resolves({ Parameter: { Value: "cached-value" } })

		await loadSecret("/my/secret")
		await loadSecret("/my/secret")

		expect(ssm.commandCalls(GetParameterCommand)).toHaveLength(1)
	})

	it("throws when the parameter is missing", async () => {
		ssm.on(GetParameterCommand).resolves({ Parameter: undefined })

		await expect(loadSecret("/missing")).rejects.toThrow(
			'SSM parameter "/missing" is empty or missing',
		)
	})
})

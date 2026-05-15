import { GetParameterCommand, SSMClient } from "@aws-sdk/client-ssm"

export const ssmClient = new SSMClient({})

const cache = new Map<string, string>()

export function clearCache(): void {
	cache.clear()
}

export async function loadSecret(name: string): Promise<string> {
	const cached = cache.get(name)
	if (cached !== undefined) return cached

	const response = await ssmClient.send(
		new GetParameterCommand({ Name: name, WithDecryption: true }),
	)
	const value = response.Parameter?.Value
	if (!value) throw new Error(`SSM parameter "${name}" is empty or missing`)

	cache.set(name, value)
	return value
}

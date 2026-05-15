type JwkKey = {
	kid: string
	kty: string
	use: string
	n: string
	e: string
}

type JwksResponse = {
	keys: JwkKey[]
}

let cache: Map<string, JwkKey> | undefined

export function clearJwksCache(): void {
	cache = undefined
}

export async function getJwk(jwksUrl: string, kid: string): Promise<JwkKey> {
	if (!cache) {
		const response = await fetch(jwksUrl)
		if (!response.ok) {
			throw new Error(
				`Failed to fetch JWKS from ${jwksUrl}: ${response.status}`,
			)
		}
		const data = (await response.json()) as JwksResponse
		cache = new Map(data.keys.map((k) => [k.kid, k]))
	}

	const key = cache.get(kid)
	if (!key) throw new Error(`JWK with kid "${kid}" not found in JWKS`)
	return key
}

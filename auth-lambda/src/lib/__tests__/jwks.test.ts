import { beforeEach, describe, expect, it, vi } from "vitest"
import { clearJwksCache, getJwk } from "../jwks.ts"

const JWKS_URL =
	"https://cognito-idp.eu-west-2.amazonaws.com/eu-west-2_test/.well-known/jwks.json"
const MOCK_KEY = { kid: "key-1", kty: "RSA", use: "sig", n: "abc", e: "AQAB" }

function mockFetch(keys: (typeof MOCK_KEY)[]): void {
	vi.stubGlobal(
		"fetch",
		vi.fn().mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ keys }),
		}),
	)
}

describe("getJwk", () => {
	beforeEach(() => {
		clearJwksCache()
		vi.restoreAllMocks()
	})

	it("returns the key matching the kid", async () => {
		mockFetch([MOCK_KEY])

		const key = await getJwk(JWKS_URL, "key-1")

		expect(key).toEqual(MOCK_KEY)
	})

	it("caches JWKS — fetch called only once for repeated calls", async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ keys: [MOCK_KEY] }),
		})
		vi.stubGlobal("fetch", fetchMock)

		await getJwk(JWKS_URL, "key-1")
		await getJwk(JWKS_URL, "key-1")

		expect(fetchMock).toHaveBeenCalledTimes(1)
	})

	it("throws when the kid is not found in JWKS", async () => {
		mockFetch([MOCK_KEY])

		await expect(getJwk(JWKS_URL, "missing-kid")).rejects.toThrow(
			'JWK with kid "missing-kid" not found in JWKS',
		)
	})

	it("throws when JWKS endpoint returns an error", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockResolvedValue({ ok: false, status: 503 }),
		)

		await expect(getJwk(JWKS_URL, "key-1")).rejects.toThrow(
			"Failed to fetch JWKS from",
		)
	})
})

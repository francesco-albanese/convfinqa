export const COOKIE = {
	ACCESS_TOKEN: "access_token",
	REFRESH_TOKEN: "refresh_token",
	PKCE_VERIFIER: "pkce_verifier",
	STATE: "state",
} as const

export const ACCESS_TOKEN_MAX_AGE = 60 * 60
export const REFRESH_TOKEN_MAX_AGE = 30 * 24 * 60 * 60
export const PKCE_MAX_AGE = 600

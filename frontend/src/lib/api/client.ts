let onUnauthed: (() => void) | null = null;
let refreshPromise: Promise<boolean> | null = null;

export function registerUnauthHandler(fn: () => void): () => void {
	onUnauthed = fn;
	return () => {
		onUnauthed = null;
	};
}

async function tryRefresh(): Promise<boolean> {
	if (refreshPromise) return refreshPromise;
	refreshPromise = fetch("/api/auth/refresh", { method: "POST" })
		.then((r) => r.ok)
		.catch(() => false)
		.finally(() => {
			refreshPromise = null;
		});
	return refreshPromise;
}

export async function apiFetch(
	input: RequestInfo | URL,
	init?: RequestInit,
): Promise<Response> {
	const res = await fetch(input, init);
	if (res.status !== 401) return res;

	const refreshed = await tryRefresh();
	if (!refreshed) {
		onUnauthed?.();
		return res;
	}
	const retryRes = await fetch(input, init);
	if (retryRes.status === 401) onUnauthed?.();
	return retryRes;
}

const TIMEOUT_MS = 35_000;

export async function checkHealth(): Promise<void> {
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
	try {
		const response = await fetch("/api/v1/healthz", {
			signal: controller.signal,
		});
		if (!response.ok) {
			throw new Error(`healthz returned ${response.status}`);
		}
	} finally {
		clearTimeout(timeoutId);
	}
}

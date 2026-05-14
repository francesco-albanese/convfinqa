export type StreamErrorClass = "concurrent" | "network" | "server" | "unknown";

type ProblemDetailsLike = {
	status?: unknown;
};

function parseProblemStatus(message: string): number | null {
	try {
		const parsed = JSON.parse(message) as ProblemDetailsLike;
		const status = parsed?.status;
		return typeof status === "number" ? status : null;
	} catch {
		return null;
	}
}

function looksLikeNetworkError(error: Error): boolean {
	if (error.name === "TypeError") return true;
	return /failed to fetch|network ?error|networkerror/i.test(error.message);
}

export function classifyStreamError(
	error: Error | undefined,
): StreamErrorClass | null {
	if (!error) return null;
	if (looksLikeNetworkError(error)) return "network";

	const status = parseProblemStatus(error.message);
	if (status === 409) return "concurrent";
	if (typeof status === "number" && status >= 500) return "server";

	return "unknown";
}

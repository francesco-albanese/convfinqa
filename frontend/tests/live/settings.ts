export type LiveE2eSettings = {
	baseUrl: string;
	email: string;
	password: string;
	localAuth: boolean;
	authStatePath: string;
	documentId: string;
};

// biome-ignore lint/complexity/useLiteralKeys: local hooks block the process env dot form.
const runtimeEnv = process["env"];
const DEFAULT_AUTH_STATE_PATH = "tests/live/.auth/user.json";
const DEFAULT_DOCUMENT_ID = "Single_JKHY/2009/page_28.pdf-3";

function requireSetting(name: string): string {
	const value = runtimeEnv[name]?.trim();
	if (!value) {
		throw new Error(`Missing required live e2e environment variable: ${name}`);
	}
	return value;
}

export function getLiveE2eSettings(): LiveE2eSettings {
	const localAuth = runtimeEnv.E2E_LOCAL_AUTH === "1";
	return {
		baseUrl: requireSetting("E2E_BASE_URL").replace(/\/$/, ""),
		email: localAuth ? "" : requireSetting("E2E_EMAIL"),
		password: localAuth ? "" : requireSetting("E2E_PASSWORD"),
		localAuth,
		authStatePath: runtimeEnv.E2E_AUTH_STATE?.trim() || DEFAULT_AUTH_STATE_PATH,
		documentId: runtimeEnv.E2E_DOCUMENT_ID?.trim() || DEFAULT_DOCUMENT_ID,
	};
}

import { afterEach, describe, expect, it } from "vitest";
import { getLiveE2eSettings } from "./settings";

// biome-ignore lint/complexity/useLiteralKeys: local hooks block the process env dot form.
const runtimeEnv = process["env"];
const originalEnv = { ...runtimeEnv };

function resetEnv(): void {
	for (const key of Object.keys(runtimeEnv)) {
		delete runtimeEnv[key];
	}
	Object.assign(runtimeEnv, originalEnv);
}

function setRequiredEnv(): void {
	delete runtimeEnv.E2E_LOCAL_AUTH;
	runtimeEnv.E2E_BASE_URL = "https://sandbox.example.test/";
	runtimeEnv.E2E_EMAIL = "e2e@example.test";
	runtimeEnv.E2E_PASSWORD = "password";
}

describe("live e2e settings", () => {
	afterEach(() => {
		resetEnv();
	});

	it.each([
		"E2E_BASE_URL",
		"E2E_EMAIL",
		"E2E_PASSWORD",
	])("fails fast when %s is missing", (name) => {
		setRequiredEnv();
		delete runtimeEnv[name];

		expect(() => getLiveE2eSettings()).toThrow(
			`Missing required live e2e environment variable: ${name}`,
		);
	});

	it("normalises the required live e2e settings", () => {
		setRequiredEnv();
		runtimeEnv.E2E_AUTH_STATE = "custom-auth-state.json";
		runtimeEnv.E2E_DOCUMENT_ID = "doc-123";

		expect(getLiveE2eSettings()).toEqual({
			baseUrl: "https://sandbox.example.test",
			email: "e2e@example.test",
			password: "password",
			localAuth: false,
			authStatePath: "custom-auth-state.json",
			documentId: "doc-123",
		});
	});

	it("allows local auth without hosted credentials", () => {
		runtimeEnv.E2E_BASE_URL = "http://localhost:5173/";
		runtimeEnv.E2E_LOCAL_AUTH = "1";
		delete runtimeEnv.E2E_EMAIL;
		delete runtimeEnv.E2E_PASSWORD;

		expect(getLiveE2eSettings()).toMatchObject({
			baseUrl: "http://localhost:5173",
			email: "",
			password: "",
			localAuth: true,
		});
	});
});

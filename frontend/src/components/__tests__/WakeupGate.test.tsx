import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WakeupGate } from "@/components/WakeupGate";

function okResponse(): Response {
	return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
}

describe("WakeupGate", () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it("shows the wakeup loader on first render before healthz resolves", () => {
		vi.stubGlobal(
			"fetch",
			vi.fn(() => new Promise(() => {})),
		);
		render(
			<WakeupGate>
				<p>App content</p>
			</WakeupGate>,
		);
		expect(screen.getByTestId("wakeup-loader")).toBeVisible();
		expect(screen.queryByText("App content")).not.toBeInTheDocument();
	});

	it("renders children and hides the loader once healthz succeeds", async () => {
		vi.stubGlobal("fetch", vi.fn().mockResolvedValue(okResponse()));
		render(
			<WakeupGate>
				<p>App content</p>
			</WakeupGate>,
		);
		await waitFor(() => expect(screen.getByText("App content")).toBeVisible());
		expect(screen.queryByTestId("wakeup-loader")).not.toBeInTheDocument();
	});

	it("shows an error message and retry button when healthz fails", async () => {
		vi.stubGlobal(
			"fetch",
			vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
		);
		render(
			<WakeupGate>
				<p>App content</p>
			</WakeupGate>,
		);
		await waitFor(() =>
			expect(screen.getByRole("button", { name: /retry/i })).toBeVisible(),
		);
		expect(
			screen.getByText(/infrastructure is taking too long/i),
		).toBeVisible();
		expect(screen.queryByText("App content")).not.toBeInTheDocument();
	});

	it("re-fires the health check and shows children after a successful retry", async () => {
		const user = userEvent.setup();
		const fetchMock = vi
			.fn()
			.mockRejectedValueOnce(new TypeError("Failed to fetch"))
			.mockResolvedValue(okResponse());
		vi.stubGlobal("fetch", fetchMock);
		render(
			<WakeupGate>
				<p>App content</p>
			</WakeupGate>,
		);
		await waitFor(() =>
			expect(screen.getByRole("button", { name: /retry/i })).toBeVisible(),
		);
		await user.click(screen.getByRole("button", { name: /retry/i }));
		await waitFor(() => expect(screen.getByText("App content")).toBeVisible());
	});
});

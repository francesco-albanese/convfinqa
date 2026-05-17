import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import { routeTree } from "@/routeTree.gen";

vi.mock("@/lib/chat/useConvfinqaChat", () => ({
	useConvfinqaChat: () => ({
		id: "stub",
		messages: [],
		status: "ready",
		setMessages: () => undefined,
		error: undefined,
		clearError: () => undefined,
		resumeStream: async () => undefined,
		regenerate: async () => undefined,
		addToolResult: async () => undefined,
		addToolOutput: async () => undefined,
		addToolApprovalResponse: async () => undefined,
		stop: async () => undefined,
		sendMessage: async () => undefined,
	}),
}));

beforeEach(() => {
	vi.stubGlobal(
		"fetch",
		vi.fn().mockImplementation((input: RequestInfo | URL) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url.includes("/api/auth/refresh")) {
				return Promise.resolve(new Response(null, { status: 401 }));
			}
			return Promise.resolve(new Response(null, { status: 401 }));
		}),
	);
});

function captureLocationHref() {
	let href = "";
	vi.stubGlobal("location", {
		get href() {
			return href;
		},
		set href(v: string) {
			href = v;
		},
		pathname: "/sign-in",
	});
	return { get: () => href };
}

function renderSignInRoute() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const router = createRouter({
		routeTree,
		history: createMemoryHistory({ initialEntries: ["/sign-in"] }),
		context: { queryClient },
	});
	const result = render(
		<AuthProvider>
			<QueryClientProvider client={queryClient}>
				<RouterProvider router={router} />
			</QueryClientProvider>
		</AuthProvider>,
	);
	return { ...result, router };
}

describe("/sign-in route", () => {
	it("renders the heading and Google sign-in button", async () => {
		renderSignInRoute();
		expect(
			await screen.findByRole("heading", { name: /welcome back/i }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /continue with google/i }),
		).toBeInTheDocument();
		expect(screen.queryByLabelText(/email/i)).not.toBeInTheDocument();
		expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
	});

	it("redirects to the BFF login when 'Continue with Google' is clicked", async () => {
		const captured = captureLocationHref();
		const user = userEvent.setup();
		renderSignInRoute();
		await screen.findByRole("heading", { name: /welcome back/i });

		await user.click(
			screen.getByRole("button", { name: /continue with google/i }),
		);

		expect(captured.get()).toBe("/api/auth/login");
	});
});

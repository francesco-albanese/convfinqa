import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
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
		vi.fn().mockResolvedValue(new Response(null, { status: 401 })),
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
		pathname: "/sign-up",
	});
	return { get: () => href };
}

function renderSignUpRoute() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const router = createRouter({
		routeTree,
		history: createMemoryHistory({ initialEntries: ["/sign-up"] }),
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

describe("/sign-up route", () => {
	it("renders the sign-up form skeleton: name, email, password, Sign up, Continue with Google", async () => {
		renderSignUpRoute();
		expect(
			await screen.findByRole("heading", { name: /create an account/i }),
		).toBeInTheDocument();
		expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
		expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
		expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /^sign up$/i }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /continue with google/i }),
		).toBeInTheDocument();
	});

	it("redirects to the BFF login when 'Sign up' is clicked", async () => {
		const captured = captureLocationHref();
		const user = userEvent.setup();
		renderSignUpRoute();
		await screen.findByRole("heading", { name: /create an account/i });

		await user.click(screen.getByRole("button", { name: /^sign up$/i }));

		expect(captured.get()).toBe("/api/auth/login");
	});

	it("redirects to the BFF login when 'Continue with Google' is clicked", async () => {
		const captured = captureLocationHref();
		const user = userEvent.setup();
		renderSignUpRoute();
		await screen.findByRole("heading", { name: /create an account/i });

		await user.click(
			screen.getByRole("button", { name: /continue with google/i }),
		);

		expect(captured.get()).toBe("/api/auth/login");
	});

	it("navigates to /sign-in when 'Sign in' footer link is clicked", async () => {
		const user = userEvent.setup();
		const { router } = renderSignUpRoute();
		await screen.findByRole("heading", { name: /create an account/i });

		await user.click(screen.getByRole("link", { name: /^sign in$/i }));

		await waitFor(() => {
			expect(router.state.location.pathname).toBe("/sign-in");
		});
	});
});

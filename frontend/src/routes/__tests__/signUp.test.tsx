import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createMemoryHistory,
	createRouter,
	RouterProvider,
} from "@tanstack/react-router";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AUTH_STORAGE_KEY, AuthProvider } from "@/lib/auth/AuthProvider";
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

	it("signs the user in and navigates to /app when 'Sign up' is clicked", async () => {
		const user = userEvent.setup();
		const { router } = renderSignUpRoute();
		await screen.findByRole("heading", { name: /create an account/i });

		await user.click(screen.getByRole("button", { name: /^sign up$/i }));

		await waitFor(() => {
			expect(router.state.location.pathname).toBe("/app");
		});
		expect(window.localStorage.getItem(AUTH_STORAGE_KEY)).toMatch(/^dev-user-/);
	});

	it("signs the user in and navigates to /app when 'Continue with Google' is clicked", async () => {
		const user = userEvent.setup();
		const { router } = renderSignUpRoute();
		await screen.findByRole("heading", { name: /create an account/i });

		await user.click(
			screen.getByRole("button", { name: /continue with google/i }),
		);

		await waitFor(() => {
			expect(router.state.location.pathname).toBe("/app");
		});
		expect(window.localStorage.getItem(AUTH_STORAGE_KEY)).toMatch(/^dev-user-/);
	});

	it("navigates to /sign-in when 'Sign in' footer link is clicked", async () => {
		const user = userEvent.setup();
		const { router } = renderSignUpRoute();
		await screen.findByRole("heading", { name: /create an account/i });

		await user.click(screen.getByRole("link", { name: /^sign in$/i }));

		await waitFor(() => {
			expect(router.state.location.pathname).toBe("/sign-in");
		});
		expect(window.localStorage.getItem(AUTH_STORAGE_KEY)).toBeNull();
	});
});

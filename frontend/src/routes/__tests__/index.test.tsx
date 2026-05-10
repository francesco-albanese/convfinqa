import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	RouterProvider,
	createMemoryHistory,
	createRouter,
} from "@tanstack/react-router";
import { routeTree } from "@/routeTree.gen";

function renderApp(initialPath: string) {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const router = createRouter({
		routeTree,
		history: createMemoryHistory({ initialEntries: [initialPath] }),
		context: { queryClient },
	});
	return render(
		<QueryClientProvider client={queryClient}>
			<RouterProvider router={router} />
		</QueryClientProvider>,
	);
}

describe("landing route /", () => {
	it("shows the placeholder copy once the route chunk loads", async () => {
		renderApp("/");
		expect(
			await screen.findByText("ConvFinQA — coming online"),
		).toBeInTheDocument();
	});
});

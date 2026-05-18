import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
	makeLargeList,
	SAMPLE_LIST,
	stubChatListFetch,
} from "./__fixtures__/sidebar";
import { renderSidebar } from "./renderSidebar";

afterEach(() => {
	vi.unstubAllGlobals();
});

describe("Sidebar", () => {
	it("invokes onNewConversation when the user clicks the primary button", async () => {
		stubChatListFetch({ items: [] });
		const user = userEvent.setup();
		const { onNewConversation } = renderSidebar();

		await user.click(screen.getByRole("button", { name: /new conversation/i }));

		expect(onNewConversation).toHaveBeenCalledTimes(1);
	});

	it("invokes onPickDocument when the user clicks the pin-document button", async () => {
		stubChatListFetch({ items: [] });
		const user = userEvent.setup();
		const { onPickDocument } = renderSidebar();

		await user.click(screen.getByRole("button", { name: /pin a document/i }));

		expect(onPickDocument).toHaveBeenCalledTimes(1);
	});

	it("invokes onToggleCollapse when the collapse button is pressed", async () => {
		stubChatListFetch({ items: [] });
		const user = userEvent.setup();
		const { onToggleCollapse } = renderSidebar();

		await user.click(screen.getByRole("button", { name: /collapse sidebar/i }));

		expect(onToggleCollapse).toHaveBeenCalledTimes(1);
	});

	it("hides the brand and search input when collapsed", async () => {
		stubChatListFetch({ items: [] });
		renderSidebar({ collapsed: true });

		expect(screen.queryByText("ConvFinQA")).not.toBeInTheDocument();
		expect(
			screen.queryByRole("searchbox", { name: /search conversations/i }),
		).not.toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /new conversation/i }),
		).toBeVisible();
		expect(
			screen.getByRole("button", { name: /expand sidebar/i }),
		).toBeVisible();
	});

	it("exposes a user menu that signs the user out", async () => {
		stubChatListFetch({ items: [] });
		const user = userEvent.setup();
		const { onSignOut } = renderSidebar({ userId: "francesco" });

		await user.click(screen.getByRole("button", { name: /open user menu/i }));
		await user.click(
			await screen.findByRole("menuitem", { name: /sign out/i }),
		);

		expect(onSignOut).toHaveBeenCalledTimes(1);
	});

	it("shows an empty-state hint when the user has no conversations", async () => {
		stubChatListFetch({ items: [] });
		renderSidebar();

		await waitFor(() => {
			expect(screen.getByText(/no conversations yet/i)).toBeInTheDocument();
		});
	});
});

describe("Sidebar — grouped chat list", () => {
	it("renders document groups with their conversations and a row count badge", async () => {
		stubChatListFetch(SAMPLE_LIST);
		renderSidebar();

		const aaaHeader = await screen.findByRole("button", {
			name: /aaa · 2024/i,
		});
		expect(aaaHeader).toHaveAttribute("aria-expanded", "true");
		expect(within(aaaHeader).getByText("2")).toBeVisible();

		expect(screen.getByText(/revenue trend for the year/i)).toBeInTheDocument();
		expect(
			screen.getByText(/operating margin commentary/i),
		).toBeInTheDocument();
		expect(screen.getByText(/debt covenants review/i)).toBeInTheDocument();
		expect(screen.getByText(/net income discussion/i)).toBeInTheDocument();
	});

	it("hides a group's conversations when its header is collapsed", async () => {
		stubChatListFetch(SAMPLE_LIST);
		const user = userEvent.setup();
		renderSidebar();

		const bbbHeader = await screen.findByRole("button", {
			name: /bbb · 2023/i,
		});
		await user.click(bbbHeader);

		expect(bbbHeader).toHaveAttribute("aria-expanded", "false");
		expect(
			screen.queryByText(/debt covenants review/i),
		).not.toBeInTheDocument();
		expect(screen.queryByText(/cash flow analysis/i)).not.toBeInTheDocument();
		expect(screen.getByText(/revenue trend for the year/i)).toBeInTheDocument();
	});

	it("narrows the visible rows when the user types a substring of a preview", async () => {
		stubChatListFetch(SAMPLE_LIST);
		const user = userEvent.setup();
		renderSidebar();

		await screen.findByText(/revenue trend for the year/i);
		const search = screen.getByRole("searchbox", {
			name: /search conversations/i,
		});

		await user.type(search, "margin");

		await waitFor(() => {
			expect(
				screen.queryByText(/revenue trend for the year/i),
			).not.toBeInTheDocument();
		});
		expect(
			screen.getByText(/operating margin commentary/i),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /bbb · 2023/i }),
		).not.toBeInTheDocument();
	});

	it("keeps the whole group's conversations when the query matches the document ticker", async () => {
		stubChatListFetch(SAMPLE_LIST);
		const user = userEvent.setup();
		renderSidebar();

		await screen.findByText(/revenue trend for the year/i);
		await user.type(
			screen.getByRole("searchbox", { name: /search conversations/i }),
			"aaa",
		);

		expect(
			await screen.findByText(/revenue trend for the year/i),
		).toBeInTheDocument();
		expect(
			screen.getByText(/operating margin commentary/i),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /bbb · 2023/i }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /ccc · 2025/i }),
		).not.toBeInTheDocument();
	});

	it("keeps the whole group's conversations when the query matches the document title", async () => {
		stubChatListFetch(SAMPLE_LIST);
		const user = userEvent.setup();
		renderSidebar();

		await screen.findByText(/revenue trend for the year/i);
		await user.type(
			screen.getByRole("searchbox", { name: /search conversations/i }),
			"bbb 2023",
		);

		expect(
			await screen.findByText(/debt covenants review/i),
		).toBeInTheDocument();
		expect(screen.getByText(/cash flow analysis/i)).toBeInTheDocument();
		expect(
			screen.queryByText(/revenue trend for the year/i),
		).not.toBeInTheDocument();
	});

	it("calls onSelectChat with both the conversation id and its document id when a row is clicked", async () => {
		stubChatListFetch(SAMPLE_LIST);
		const user = userEvent.setup();
		const { onSelectChat } = renderSidebar();

		const row = await screen.findByText(/net income discussion/i);
		await user.click(row);

		expect(onSelectChat).toHaveBeenCalledWith("conv-c1", "doc-ccc");
	});

	it("shows the no-match copy when the filter excludes every conversation", async () => {
		stubChatListFetch(SAMPLE_LIST);
		const user = userEvent.setup();
		renderSidebar();

		await screen.findByText(/revenue trend for the year/i);
		await user.type(
			screen.getByRole("searchbox", { name: /search conversations/i }),
			"zzznomatch",
		);

		expect(
			await screen.findByText(/no conversations match your filter/i),
		).toBeInTheDocument();
	});

	it("does not virtualize the list at the small fixture size", async () => {
		stubChatListFetch(SAMPLE_LIST);
		renderSidebar();

		await screen.findByText(/revenue trend for the year/i);
		expect(
			screen.queryByTestId("sidebar-virtual-scroll"),
		).not.toBeInTheDocument();
	});

	it("remembers a collapsed group across a remount for the same user", async () => {
		stubChatListFetch(SAMPLE_LIST);
		const user = userEvent.setup();

		const { unmount } = renderSidebar();
		const bbbHeader = await screen.findByRole("button", {
			name: /bbb · 2023/i,
		});
		await user.click(bbbHeader);
		expect(bbbHeader).toHaveAttribute("aria-expanded", "false");
		unmount();

		renderSidebar();

		const remountedBbb = await screen.findByRole("button", {
			name: /bbb · 2023/i,
		});
		expect(remountedBbb).toHaveAttribute("aria-expanded", "false");
		expect(
			screen.queryByText(/debt covenants review/i),
		).not.toBeInTheDocument();
	});

	it("switches to a virtualized list when the flattened row count exceeds 50", async () => {
		stubChatListFetch(makeLargeList(60));
		renderSidebar();

		expect(
			await screen.findByTestId("sidebar-virtual-scroll"),
		).toBeInTheDocument();
	});
});

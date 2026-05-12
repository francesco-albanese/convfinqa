import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "@/components/Sidebar";

function renderSidebar(
	props: Partial<React.ComponentProps<typeof Sidebar>> = {},
) {
	const onToggleCollapse = props.onToggleCollapse ?? vi.fn();
	const onNewConversation = props.onNewConversation ?? vi.fn();
	const onSignOut = props.onSignOut ?? vi.fn();
	render(
		<Sidebar
			chats={props.chats ?? []}
			collapsed={props.collapsed ?? false}
			userId={props.userId ?? "dev-user"}
			onToggleCollapse={onToggleCollapse}
			onNewConversation={onNewConversation}
			onSignOut={onSignOut}
		/>,
	);
	return { onToggleCollapse, onNewConversation, onSignOut };
}

describe("Sidebar", () => {
	it("renders the brand, new-conversation button, and empty-list copy when there are no chats", () => {
		renderSidebar();

		expect(screen.getByText("ConvFinQA")).toBeVisible();
		expect(
			screen.getByRole("button", { name: /new conversation/i }),
		).toBeVisible();
		expect(screen.getByText(/no conversations yet/i)).toBeVisible();
	});

	it("invokes onNewConversation when the user clicks the primary button", async () => {
		const user = userEvent.setup();
		const { onNewConversation } = renderSidebar();

		await user.click(screen.getByRole("button", { name: /new conversation/i }));

		expect(onNewConversation).toHaveBeenCalledTimes(1);
	});

	it("lets the user type into the search input", async () => {
		const user = userEvent.setup();
		renderSidebar();

		const search = screen.getByRole("searchbox", {
			name: /search conversations/i,
		});
		await user.type(search, "revenue");

		expect(search).toHaveValue("revenue");
		expect(search).toHaveFocus();
	});

	it("invokes onToggleCollapse when the collapse button is pressed", async () => {
		const user = userEvent.setup();
		const { onToggleCollapse } = renderSidebar();

		await user.click(screen.getByRole("button", { name: /collapse sidebar/i }));

		expect(onToggleCollapse).toHaveBeenCalledTimes(1);
	});

	it("hides the brand and search input when collapsed but keeps the icon-only new-conversation button", () => {
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
		const user = userEvent.setup();
		const { onSignOut } = renderSidebar({ userId: "francesco" });

		await user.click(screen.getByRole("button", { name: /open user menu/i }));
		await user.click(
			await screen.findByRole("menuitem", { name: /sign out/i }),
		);

		expect(onSignOut).toHaveBeenCalledTimes(1);
	});
});

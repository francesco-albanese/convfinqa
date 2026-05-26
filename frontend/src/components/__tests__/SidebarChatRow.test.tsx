import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatRow } from "@/components/SidebarChatRow";
import type { ChatDocumentGroup } from "@/lib/transforms/groupByDocument";

type Chat = ChatDocumentGroup["conversations"][number];

function makeChat(overrides: Partial<Chat>): Chat {
	return {
		id: "conv-1",
		document: { id: "doc-1", ticker: "AAA", year: 2024, title: "AAA 2024" },
		last_message_preview: "what was revenue in 2024",
		last_message_at: "2026-05-14T08:00:00+00:00",
		title: null,
		...overrides,
	};
}

describe("ChatRow", () => {
	it("renders the auto-generated title when present", () => {
		render(
			<ChatRow
				chat={makeChat({ title: "2024 revenue overview" })}
				documentId="doc-1"
				onSelectChat={vi.fn()}
			/>,
		);

		const row = screen.getByTestId("sidebar-chat-row");
		expect(row).toHaveTextContent("2024 revenue overview");
		expect(row).toHaveAttribute(
			"aria-label",
			"Open conversation: 2024 revenue overview",
		);
		expect(row).not.toHaveTextContent("what was revenue in 2024");
	});

	it("falls back to the last message preview when title is null", () => {
		render(
			<ChatRow
				chat={makeChat({ title: null })}
				documentId="doc-1"
				onSelectChat={vi.fn()}
			/>,
		);

		const row = screen.getByTestId("sidebar-chat-row");
		expect(row).toHaveTextContent("what was revenue in 2024");
		expect(row).toHaveAttribute(
			"aria-label",
			"Open conversation: what was revenue in 2024",
		);
	});

	it("does not render a delete control when onDeleteChat is absent", () => {
		render(
			<ChatRow chat={makeChat({})} documentId="doc-1" onSelectChat={vi.fn()} />,
		);

		expect(screen.queryByTestId("sidebar-chat-delete")).not.toBeInTheDocument();
	});

	it("selecting the row is not triggered by clicking delete", async () => {
		const onSelectChat = vi.fn();
		const onDeleteChat = vi.fn();
		const user = userEvent.setup();
		render(
			<ChatRow
				chat={makeChat({ id: "conv-9" })}
				documentId="doc-1"
				onSelectChat={onSelectChat}
				onDeleteChat={onDeleteChat}
			/>,
		);

		await user.click(screen.getByTestId("sidebar-chat-delete"));

		expect(onSelectChat).not.toHaveBeenCalled();
		expect(onDeleteChat).not.toHaveBeenCalled();
	});

	it("deletes only after confirming, and cancel aborts", async () => {
		const onDeleteChat = vi.fn();
		const user = userEvent.setup();
		render(
			<ChatRow
				chat={makeChat({ id: "conv-9" })}
				documentId="doc-1"
				onSelectChat={vi.fn()}
				onDeleteChat={onDeleteChat}
			/>,
		);

		await user.click(screen.getByTestId("sidebar-chat-delete"));
		await user.click(screen.getByRole("button", { name: "Cancel" }));
		expect(onDeleteChat).not.toHaveBeenCalled();

		await user.click(screen.getByTestId("sidebar-chat-delete"));
		await user.click(screen.getByRole("button", { name: "Delete" }));
		expect(onDeleteChat).toHaveBeenCalledWith("conv-9");
	});
});

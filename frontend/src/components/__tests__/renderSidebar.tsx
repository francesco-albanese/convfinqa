import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { vi } from "vitest";
import { Sidebar } from "@/components/Sidebar";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import { TEST_USER_ID } from "./__fixtures__/sidebar";

export type SidebarHandlers = {
	onToggleCollapse: () => void;
	onNewConversation: () => void;
	onPickDocument: () => void;
	onSelectChat: (chatId: string, documentId: string) => void;
	onDeleteChat: (chatId: string) => void;
	onSignOut: () => void;
};

export function renderSidebar(
	props: Partial<React.ComponentProps<typeof Sidebar>> = {},
): SidebarHandlers & { unmount: () => void } {
	const handlers: SidebarHandlers = {
		onToggleCollapse: vi.fn(),
		onNewConversation: vi.fn(),
		onPickDocument: vi.fn(),
		onSelectChat: vi.fn(),
		onDeleteChat: vi.fn(),
		onSignOut: vi.fn(),
	};
	const client = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	const { unmount } = render(
		<QueryClientProvider client={client}>
			<AuthProvider>
				<Sidebar
					collapsed={props.collapsed ?? false}
					userId={props.userId ?? TEST_USER_ID}
					email={props.email ?? null}
					onToggleCollapse={props.onToggleCollapse ?? handlers.onToggleCollapse}
					onNewConversation={
						props.onNewConversation ?? handlers.onNewConversation
					}
					onPickDocument={props.onPickDocument ?? handlers.onPickDocument}
					onSelectChat={props.onSelectChat ?? handlers.onSelectChat}
					onDeleteChat={props.onDeleteChat ?? handlers.onDeleteChat}
					onSignOut={props.onSignOut ?? handlers.onSignOut}
				/>
			</AuthProvider>
		</QueryClientProvider>,
	);
	return { ...handlers, unmount };
}

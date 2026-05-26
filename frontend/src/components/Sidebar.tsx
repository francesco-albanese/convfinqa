import { PanelLeftClose, PanelLeftOpen, Pin, Plus, Search } from "lucide-react";
import { useId, useState } from "react";
import { SidebarChatList } from "@/components/SidebarChatList";
import { UserMenu } from "@/components/UserMenu";
import { cn } from "@/lib/utils";

type SidebarProps = {
	collapsed: boolean;
	userId: string;
	email: string | null;
	onToggleCollapse: () => void;
	onNewConversation: () => void;
	onPickDocument: () => void;
	onSelectChat: (chatId: string, documentId: string) => void;
	onDeleteChat: (chatId: string) => void;
	onSignOut: () => void;
};

export function Sidebar({
	collapsed,
	userId,
	email,
	onToggleCollapse,
	onNewConversation,
	onPickDocument,
	onSelectChat,
	onDeleteChat,
	onSignOut,
}: SidebarProps) {
	const searchId = useId();
	const [query, setQuery] = useState("");

	const ToggleIcon = collapsed ? PanelLeftOpen : PanelLeftClose;

	return (
		<nav
			aria-label="Sidebar"
			data-testid="sidebar"
			data-collapsed={collapsed ? "true" : "false"}
			className="flex h-full min-h-0 flex-col gap-3 border-border border-r bg-card py-3"
		>
			<div
				className={cn(
					"flex items-center gap-2",
					collapsed ? "justify-center px-2" : "justify-between px-3",
				)}
			>
				{!collapsed && (
					<span className="font-semibold text-foreground text-sm tracking-tight">
						ConvFinQA
					</span>
				)}
				<button
					type="button"
					onClick={onToggleCollapse}
					aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
					aria-expanded={!collapsed}
					className="hidden h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring lg:inline-flex"
				>
					<ToggleIcon aria-hidden="true" className="size-4" />
				</button>
			</div>

			<div className={cn("flex flex-col gap-2", collapsed ? "px-2" : "px-3")}>
				<button
					type="button"
					onClick={onNewConversation}
					aria-label="New conversation"
					data-modal-initial-focus
					className={cn(
						"inline-flex h-9 items-center gap-2 rounded-md bg-primary font-medium text-primary-foreground text-sm hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
						collapsed ? "w-9 justify-center px-0" : "w-full justify-start px-3",
					)}
				>
					<Plus aria-hidden="true" className="size-4" />
					{!collapsed && <span>New conversation</span>}
				</button>

				<button
					type="button"
					onClick={onPickDocument}
					aria-label="Pin a document"
					className={cn(
						"inline-flex h-9 items-center gap-2 rounded-md border border-border bg-card font-medium text-foreground text-sm hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
						collapsed ? "w-9 justify-center px-0" : "w-full justify-start px-3",
					)}
				>
					<Pin aria-hidden="true" className="size-4" />
					{!collapsed && <span>Pin a document</span>}
				</button>

				{!collapsed && (
					<div className="relative">
						<label htmlFor={searchId} className="sr-only">
							Search conversations
						</label>
						<Search
							aria-hidden="true"
							className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
						/>
						<input
							id={searchId}
							type="search"
							value={query}
							onChange={(event) => setQuery(event.target.value)}
							placeholder="Search conversations"
							className="h-9 w-full rounded-md border border-border bg-input pr-3 pl-8 text-foreground text-sm placeholder:text-muted-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
						/>
					</div>
				)}
			</div>

			<div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
				<SidebarChatList
					query={query}
					collapsed={collapsed}
					onSelectChat={onSelectChat}
					onDeleteChat={onDeleteChat}
				/>
			</div>

			<div className="border-border border-t px-2 pt-2">
				<UserMenu
					userId={userId}
					email={email}
					collapsed={collapsed}
					onSignOut={onSignOut}
				/>
			</div>
		</nav>
	);
}

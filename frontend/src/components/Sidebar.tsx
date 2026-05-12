import { PanelLeftClose, PanelLeftOpen, Plus, Search } from "lucide-react";
import { useId, useState } from "react";
import { UserMenu } from "@/components/UserMenu";
import { cn } from "@/lib/utils";

export type SidebarChatItem = {
	id: string;
	title: string;
};

export type SidebarChatGroup = {
	documentId: string;
	documentTitle: string;
	chats: SidebarChatItem[];
};

type SidebarProps = {
	chats: SidebarChatGroup[];
	collapsed: boolean;
	userId: string;
	onToggleCollapse: () => void;
	onNewConversation: () => void;
	onSignOut: () => void;
};

export function Sidebar({
	chats,
	collapsed,
	userId,
	onToggleCollapse,
	onNewConversation,
	onSignOut,
}: SidebarProps) {
	const searchId = useId();
	const [query, setQuery] = useState("");

	const ToggleIcon = collapsed ? PanelLeftOpen : PanelLeftClose;
	const isEmpty = chats.length === 0;

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
					className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
				>
					<ToggleIcon aria-hidden="true" className="size-4" />
				</button>
			</div>

			<div className={cn("flex flex-col gap-2", collapsed ? "px-2" : "px-3")}>
				<button
					type="button"
					onClick={onNewConversation}
					aria-label="New conversation"
					className={cn(
						"inline-flex h-9 items-center gap-2 rounded-md bg-primary font-medium text-primary-foreground text-sm hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
						collapsed ? "w-9 justify-center px-0" : "w-full justify-start px-3",
					)}
				>
					<Plus aria-hidden="true" className="size-4" />
					{!collapsed && <span>New conversation</span>}
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

			<div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-1">
				{isEmpty ? (
					!collapsed && (
						<p className="px-3 py-2 text-muted-foreground text-xs">
							No conversations yet
						</p>
					)
				) : (
					<ul className="flex flex-col gap-1">
						{chats.flatMap((group) =>
							group.chats.map((chat) => (
								<li
									key={chat.id}
									className="truncate rounded-md px-3 py-1.5 text-foreground text-sm hover:bg-secondary"
								>
									{chat.title}
								</li>
							)),
						)}
					</ul>
				)}
			</div>

			<div className="border-border border-t px-2 pt-2">
				<UserMenu userId={userId} collapsed={collapsed} onSignOut={onSignOut} />
			</div>
		</nav>
	);
}

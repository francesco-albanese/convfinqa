import { useVirtualizer } from "@tanstack/react-virtual";
import { Loader2 } from "lucide-react";
import { useMemo, useRef } from "react";
import { useAuthedUserId } from "@/lib/auth/AuthProvider";
import {
	type FlattenedRow,
	filterGroups,
	flattenRows,
} from "@/lib/chat/chatListHelpers";
import { useChatList } from "@/lib/queries/chats";
import { groupByDocument } from "@/lib/transforms/groupByDocument";
import { useCollapsedGroups } from "@/lib/ui/collapsedGroupsStore";
import { ChatRow, DocGroupHeader } from "./SidebarChatRow";

const VIRTUAL_THRESHOLD = 50;
const ROW_HEIGHT_PX = 56;
const VIRTUAL_LIST_HEIGHT_PX = 480;

export type SidebarChatListProps = {
	query: string;
	collapsed: boolean;
	onSelectChat: (chatId: string, documentId: string) => void;
	onDeleteChat: (chatId: string) => void;
};

export function SidebarChatList({
	query,
	collapsed,
	onSelectChat,
	onDeleteChat,
}: SidebarChatListProps) {
	const { data, isLoading, isError } = useChatList();
	const userId = useAuthedUserId();
	const { collapsedGroups, toggleGroup } = useCollapsedGroups(userId);

	const groups = useMemo(
		() => groupByDocument(data?.items ?? []),
		[data?.items],
	);
	const visibleGroups = useMemo(
		() => filterGroups(groups, query),
		[groups, query],
	);
	const rows = useMemo(
		() => flattenRows(visibleGroups, collapsedGroups),
		[visibleGroups, collapsedGroups],
	);

	if (collapsed) {
		return null;
	}

	if (isLoading) {
		return (
			<div
				role="status"
				aria-live="polite"
				className="flex items-center gap-2 px-3 py-2 text-muted-foreground text-xs"
			>
				<Loader2 aria-hidden="true" className="size-3 animate-spin" />
				<span>Loading conversations…</span>
			</div>
		);
	}

	if (isError) {
		return (
			<p className="px-3 py-2 text-muted-foreground text-xs">
				Couldn't load conversations.
			</p>
		);
	}

	if (rows.length === 0) {
		const emptyCopy =
			groups.length === 0
				? "No conversations yet"
				: "No conversations match your filter";
		return (
			<p className="px-3 py-2 text-muted-foreground text-xs">{emptyCopy}</p>
		);
	}

	if (rows.length > VIRTUAL_THRESHOLD) {
		return (
			<VirtualizedRows
				rows={rows}
				onToggleGroup={toggleGroup}
				onSelectChat={onSelectChat}
				onDeleteChat={onDeleteChat}
			/>
		);
	}

	return (
		<ul className="flex flex-col gap-1 px-1">
			{rows.map((row) =>
				row.kind === "header" ? (
					<DocGroupHeader
						key={`h-${row.group.document.id}`}
						group={row.group}
						isCollapsed={row.isCollapsed}
						onToggle={toggleGroup}
					/>
				) : (
					<ChatRow
						key={row.chat.id}
						chat={row.chat}
						documentId={row.groupId}
						onSelectChat={onSelectChat}
						onDeleteChat={onDeleteChat}
					/>
				),
			)}
		</ul>
	);
}

type VirtualizedRowsProps = {
	rows: FlattenedRow[];
	onToggleGroup: (documentId: string) => void;
	onSelectChat: (chatId: string, documentId: string) => void;
	onDeleteChat: (chatId: string) => void;
};

function VirtualizedRows({
	rows,
	onToggleGroup,
	onSelectChat,
	onDeleteChat,
}: VirtualizedRowsProps) {
	const scrollRef = useRef<HTMLDivElement>(null);
	const virtualizer = useVirtualizer({
		count: rows.length,
		getScrollElement: () => scrollRef.current,
		estimateSize: () => ROW_HEIGHT_PX,
		overscan: 6,
	});

	const virtualItems = virtualizer.getVirtualItems();
	const renderedItems =
		virtualItems.length === 0
			? rows.map((_, index) => ({
					index,
					start: index * ROW_HEIGHT_PX,
					size: ROW_HEIGHT_PX,
					key: index,
				}))
			: virtualItems;

	return (
		<div
			ref={scrollRef}
			data-testid="sidebar-virtual-scroll"
			className="overflow-y-auto px-1"
			style={{ height: `${VIRTUAL_LIST_HEIGHT_PX}px` }}
		>
			<ul
				className="relative w-full"
				style={{
					height: `${virtualizer.getTotalSize() || rows.length * ROW_HEIGHT_PX}px`,
				}}
			>
				{renderedItems.map((virtualRow) => {
					const row = rows[virtualRow.index];
					if (!row) return null;
					return (
						<li
							key={
								row.kind === "header"
									? `h-${row.group.document.id}`
									: row.chat.id
							}
							className="absolute inset-x-0"
							style={{
								transform: `translateY(${virtualRow.start}px)`,
								height: `${virtualRow.size}px`,
							}}
						>
							{row.kind === "header" ? (
								<DocGroupHeader
									group={row.group}
									isCollapsed={row.isCollapsed}
									onToggle={onToggleGroup}
								/>
							) : (
								<ChatRow
									chat={row.chat}
									documentId={row.groupId}
									onSelectChat={onSelectChat}
									onDeleteChat={onDeleteChat}
								/>
							)}
						</li>
					);
				})}
			</ul>
		</div>
	);
}

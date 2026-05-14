import { useVirtualizer } from "@tanstack/react-virtual";
import { ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { useChatList } from "@/lib/queries/chats";
import {
	type ChatDocumentGroup,
	groupByDocument,
} from "@/lib/transforms/groupByDocument";
import { cn } from "@/lib/utils";

const VIRTUAL_THRESHOLD = 50;
const ROW_HEIGHT_PX = 56;
const VIRTUAL_LIST_HEIGHT_PX = 480;

export type SidebarChatListProps = {
	query: string;
	collapsed: boolean;
	onSelectChat: (chatId: string, documentId: string) => void;
};

type FlattenedRow =
	| { kind: "header"; group: ChatDocumentGroup; isCollapsed: boolean }
	| {
			kind: "chat";
			groupId: string;
			chat: ChatDocumentGroup["conversations"][number];
	  };

function documentLabel(document: ChatDocumentGroup["document"]): string {
	if (document.ticker && document.year !== null) {
		return `${document.ticker} · ${document.year}`;
	}
	return document.title ?? document.ticker ?? document.id;
}

function formatTimestamp(iso: string): string {
	const parsed = new Date(iso);
	if (Number.isNaN(parsed.getTime())) {
		return "";
	}
	return parsed.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
	});
}

function documentMatches(
	document: ChatDocumentGroup["document"],
	needle: string,
): boolean {
	const title = document.title?.toLowerCase() ?? "";
	const ticker = document.ticker?.toLowerCase() ?? "";
	return title.includes(needle) || ticker.includes(needle);
}

function filterGroups(
	groups: ChatDocumentGroup[],
	query: string,
): ChatDocumentGroup[] {
	const needle = query.trim().toLowerCase();
	if (needle.length === 0) {
		return groups;
	}
	const filtered: ChatDocumentGroup[] = [];
	for (const group of groups) {
		if (documentMatches(group.document, needle)) {
			filtered.push(group);
			continue;
		}
		const conversations = group.conversations.filter((conversation) =>
			conversation.last_message_preview.toLowerCase().includes(needle),
		);
		if (conversations.length > 0) {
			filtered.push({ document: group.document, conversations });
		}
	}
	return filtered;
}

function flattenRows(
	groups: ChatDocumentGroup[],
	collapsedGroups: Set<string>,
): FlattenedRow[] {
	const rows: FlattenedRow[] = [];
	for (const group of groups) {
		const isCollapsed = collapsedGroups.has(group.document.id);
		rows.push({ kind: "header", group, isCollapsed });
		if (!isCollapsed) {
			for (const chat of group.conversations) {
				rows.push({ kind: "chat", groupId: group.document.id, chat });
			}
		}
	}
	return rows;
}

export function SidebarChatList({
	query,
	collapsed,
	onSelectChat,
}: SidebarChatListProps) {
	const { data, isLoading, isError } = useChatList();
	const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
		() => new Set(),
	);

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

	const toggleGroup = (documentId: string) => {
		setCollapsedGroups((current) => {
			const next = new Set(current);
			if (next.has(documentId)) {
				next.delete(documentId);
			} else {
				next.add(documentId);
			}
			return next;
		});
	};

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
				Couldn’t load conversations.
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
};

function VirtualizedRows({
	rows,
	onToggleGroup,
	onSelectChat,
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
								/>
							)}
						</li>
					);
				})}
			</ul>
		</div>
	);
}

type DocGroupHeaderProps = {
	group: ChatDocumentGroup;
	isCollapsed: boolean;
	onToggle: (documentId: string) => void;
};

function DocGroupHeader({ group, isCollapsed, onToggle }: DocGroupHeaderProps) {
	const Chevron = isCollapsed ? ChevronRight : ChevronDown;
	return (
		<button
			type="button"
			onClick={() => onToggle(group.document.id)}
			aria-expanded={!isCollapsed}
			aria-controls={`group-${group.document.id}`}
			className={cn(
				"flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-left",
				"font-medium text-muted-foreground text-xs uppercase tracking-wide",
				"hover:bg-secondary hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
			)}
		>
			<Chevron aria-hidden="true" className="size-3" />
			<span className="truncate">{documentLabel(group.document)}</span>
			<span className="ml-auto text-muted-foreground/70 tabular-nums">
				{group.conversations.length}
			</span>
		</button>
	);
}

type ChatRowProps = {
	chat: ChatDocumentGroup["conversations"][number];
	documentId: string;
	onSelectChat: (chatId: string, documentId: string) => void;
};

function ChatRow({ chat, documentId, onSelectChat }: ChatRowProps) {
	const preview = chat.last_message_preview.trim() || "(no messages)";
	const timestamp = formatTimestamp(chat.last_message_at);
	return (
		<button
			type="button"
			onClick={() => onSelectChat(chat.id, documentId)}
			aria-label={`Open conversation: ${preview}`}
			data-testid="sidebar-chat-row"
			data-chat-id={chat.id}
			className={cn(
				"flex w-full flex-col items-start gap-0.5 rounded-md px-3 py-2 text-left",
				"hover:bg-secondary focus-visible:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
			)}
		>
			<span className="line-clamp-2 w-full text-foreground text-sm">
				{preview}
			</span>
			<span className="text-muted-foreground text-xs">{timestamp}</span>
		</button>
	);
}

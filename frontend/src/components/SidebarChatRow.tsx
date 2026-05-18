import { ChevronDown, ChevronRight } from "lucide-react";
import { documentLabel, formatTimestamp } from "@/lib/chat/chatListHelpers";
import type { ChatDocumentGroup } from "@/lib/transforms/groupByDocument";
import { cn } from "@/lib/utils";

export type DocGroupHeaderProps = {
	group: ChatDocumentGroup;
	isCollapsed: boolean;
	onToggle: (documentId: string) => void;
};

export function DocGroupHeader({
	group,
	isCollapsed,
	onToggle,
}: DocGroupHeaderProps) {
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

export type ChatRowProps = {
	chat: ChatDocumentGroup["conversations"][number];
	documentId: string;
	onSelectChat: (chatId: string, documentId: string) => void;
};

export function ChatRow({ chat, documentId, onSelectChat }: ChatRowProps) {
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

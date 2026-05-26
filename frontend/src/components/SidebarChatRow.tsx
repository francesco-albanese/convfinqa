import { ChevronDown, ChevronRight, Trash2 } from "lucide-react";
import { useState } from "react";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
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
	onDeleteChat?: (chatId: string) => void;
};

export function ChatRow({
	chat,
	documentId,
	onSelectChat,
	onDeleteChat,
}: ChatRowProps) {
	const [confirmOpen, setConfirmOpen] = useState(false);
	const preview = chat.last_message_preview.trim() || "(no messages)";
	const label = chat.title?.trim() || preview;
	const timestamp = formatTimestamp(chat.last_message_at);

	return (
		<div
			className={cn(
				"group relative flex items-center rounded-md",
				"hover:bg-secondary focus-within:bg-secondary",
			)}
		>
			<button
				type="button"
				onClick={() => onSelectChat(chat.id, documentId)}
				aria-label={`Open conversation: ${label}`}
				data-testid="sidebar-chat-row"
				data-chat-id={chat.id}
				className={cn(
					"flex min-w-0 flex-1 flex-col items-start gap-0.5 rounded-md py-2 pr-9 pl-3 text-left",
					"focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
				)}
			>
				<span className="line-clamp-2 w-full text-foreground text-sm">
					{label}
				</span>
				<span className="text-muted-foreground text-xs">{timestamp}</span>
			</button>
			{onDeleteChat ? (
				<>
					<button
						type="button"
						onClick={(event) => {
							event.stopPropagation();
							setConfirmOpen(true);
						}}
						aria-label={`Delete conversation: ${label}`}
						data-testid="sidebar-chat-delete"
						className={cn(
							"absolute right-1.5 inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity",
							"hover:bg-background hover:text-foreground focus-visible:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
							"group-hover:opacity-100 group-focus-within:opacity-100",
						)}
					>
						<Trash2 aria-hidden="true" className="size-4" />
					</button>
					<Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
						<DialogContent className="max-w-sm">
							<DialogHeader>
								<DialogTitle>Delete conversation?</DialogTitle>
								<DialogDescription>
									This permanently deletes “{label}” and all its messages. This
									action cannot be undone.
								</DialogDescription>
							</DialogHeader>
							<div className="flex justify-end gap-2 px-5 pb-5">
								<button
									type="button"
									onClick={() => setConfirmOpen(false)}
									className="inline-flex h-9 items-center rounded-md border border-border bg-card px-3 font-medium text-foreground text-sm hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={() => {
										setConfirmOpen(false);
										onDeleteChat(chat.id);
									}}
									className="inline-flex h-9 items-center rounded-md bg-destructive px-3 font-medium text-destructive-foreground text-sm hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
								>
									Delete
								</button>
							</div>
						</DialogContent>
					</Dialog>
				</>
			) : null}
		</div>
	);
}

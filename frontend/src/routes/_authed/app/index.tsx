import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import type { UIMessage } from "ai";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Composer } from "@/components/Composer";
import { EmptyState } from "@/components/EmptyState";
import { MessageList } from "@/components/MessageList";
import { StopButton } from "@/components/StopButton";
import { StreamErrorBanner } from "@/components/StreamErrorBanner";
import { useAuthedUserId } from "@/lib/auth/AuthProvider";
import {
	type AppSearch,
	AppSearchSchema,
	ChatDataPartSchema,
	ConversationDataSchema,
} from "@/lib/chat/schemas";
import { useConvfinqaChat } from "@/lib/chat/useConvfinqaChat";
import { useStreamErrorRetry } from "@/lib/chat/useStreamErrorRetry";
import { type ChatMessage, useChatMessages } from "@/lib/queries/chats";
import { openDocPicker } from "@/lib/ui/docPickerStore";

export const Route = createFileRoute("/_authed/app/")({
	validateSearch: (raw: Record<string, unknown>): AppSearch => {
		const parsed = AppSearchSchema.safeParse(raw);
		return parsed.success ? parsed.data : {};
	},
	component: AppChatPage,
});

function toUIMessage(message: ChatMessage): UIMessage {
	const role = message.role === "user" ? "user" : "assistant";
	return {
		id: message.id,
		role,
		parts: [{ type: "text", text: message.content }],
	};
}

function AppChatPage() {
	const { chatId, documentId } = Route.useSearch();
	const navigate = Route.useNavigate();
	const queryClient = useQueryClient();
	const userId = useAuthedUserId();

	const seededChatIdRef = useRef<string | null>(null);

	const handleData = useCallback(
		(part: unknown) => {
			const partResult = ChatDataPartSchema.safeParse(part);
			if (!partResult.success || partResult.data.type !== "data-conversation") {
				return;
			}
			const dataResult = ConversationDataSchema.safeParse(partResult.data.data);
			if (!dataResult.success || dataResult.data.conversationId === chatId) {
				return;
			}
			seededChatIdRef.current = dataResult.data.conversationId;
			void navigate({
				search: (prev) => ({ ...prev, chatId: dataResult.data.conversationId }),
				replace: true,
			});
		},
		[chatId, navigate],
	);

	const handleFinish = useCallback(() => {
		void queryClient.invalidateQueries({ queryKey: ["chats"] });
	}, [queryClient]);

	const chat = useConvfinqaChat({
		getUserId: () => userId,
		getDocumentId: () => documentId ?? null,
		getConversationId: () => chatId ?? null,
		onData: handleData,
		onFinish: handleFinish,
	});

	const chatRef = useRef(chat);
	chatRef.current = chat;

	const messagesQuery = useChatMessages(chatId ?? null);

	useEffect(() => {
		if (!chatId || seededChatIdRef.current === chatId || !messagesQuery.data) {
			return;
		}
		chatRef.current.setMessages(messagesQuery.data.items.map(toUIMessage));
		seededChatIdRef.current = chatId;
	}, [chatId, messagesQuery.data]);

	const handleSend = (text: string) => {
		void chat.sendMessage({ text });
	};

	const [stoppedIds, setStoppedIds] = useState<ReadonlySet<string>>(
		() => new Set<string>(),
	);

	const recordStopped = useCallback((messageId: string) => {
		setStoppedIds((prev) => {
			if (prev.has(messageId)) return prev;
			const next = new Set(prev);
			next.add(messageId);
			return next;
		});
	}, []);

	const streamingMessageId = useMemo(
		() => findLastAssistantId(chat.messages),
		[chat.messages],
	);

	const { retry, dismiss, isRetrying } = useStreamErrorRetry({
		chat,
		chatId: chatId ?? null,
	});

	return (
		<main className="flex h-full min-h-0 flex-col bg-background text-foreground">
			<header className="border-border border-b py-3 pr-6 pl-16 lg:pl-6">
				<h1 className="font-semibold text-base">ConvFinQA</h1>
				<p className="text-muted-foreground text-xs">
					{documentId
						? `Pinned: ${documentId}`
						: "Pin a document to start asking questions."}
				</p>
			</header>
			<section
				aria-label="Conversation"
				className="flex-1 overflow-y-auto px-6 py-4"
			>
				{!documentId && chat.messages.length === 0 ? (
					<EmptyState onPinDocument={openDocPicker} />
				) : (
					<MessageList
						messages={chat.messages}
						status={chat.status}
						stoppedIds={stoppedIds}
					/>
				)}
			</section>
			<section className="flex flex-col gap-2 border-border border-t bg-background px-6 py-3">
				<StreamErrorBanner
					error={chat.error}
					onRetry={retry}
					onDismiss={dismiss}
					isRetrying={isRetrying}
				/>
				<StopButton
					status={chat.status}
					stop={chat.stop}
					streamingMessageId={streamingMessageId}
					onStopped={recordStopped}
					className="self-end"
				/>
				<Composer onSend={handleSend} disabled={!documentId} />
			</section>
		</main>
	);
}

function findLastAssistantId(messages: UIMessage[]): string | null {
	for (let i = messages.length - 1; i >= 0; i--) {
		if (messages[i]?.role === "assistant") return messages[i]?.id ?? null;
	}
	return null;
}

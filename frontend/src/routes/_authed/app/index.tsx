import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import type {
	DynamicToolUIPart,
	ReasoningUIPart,
	TextUIPart,
	UIMessage,
} from "ai";
import { X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Composer } from "@/components/Composer";
import { EmptyState } from "@/components/EmptyState";
import { MessageList } from "@/components/MessageList";
import { ModelPicker } from "@/components/ModelPicker";
import { StopButton } from "@/components/StopButton";
import { StreamErrorBanner } from "@/components/StreamErrorBanner";
import { useAuthedUserId } from "@/lib/auth/AuthProvider";
import {
	clearChatResetControls,
	registerChatResetControls,
	resetConversation,
} from "@/lib/chat/conversationReset";
import {
	type AppSearch,
	AppSearchSchema,
	ChatDataPartSchema,
	type CitationData,
	CitationDataSchema,
	ConversationDataSchema,
} from "@/lib/chat/schemas";
import { useConvfinqaChat } from "@/lib/chat/useConvfinqaChat";
import { useStreamErrorRetry } from "@/lib/chat/useStreamErrorRetry";
import {
	type ChatMessage,
	type StoredCitationPart,
	useChatMessages,
} from "@/lib/queries/chats";
import { closeDocPicker, openDocPicker } from "@/lib/ui/docPickerStore";
import { useSelectedModel } from "@/lib/ui/modelStore";
import {
	closeRightPanelSheet,
	closeSidebarDrawer,
	openRightPanelSheet,
} from "@/lib/ui/responsiveStore";

export const Route = createFileRoute("/_authed/app/")({
	validateSearch: (raw: Record<string, unknown>): AppSearch => {
		const parsed = AppSearchSchema.safeParse(raw);
		return parsed.success ? parsed.data : {};
	},
	component: AppChatPage,
});

function safeParseJson(raw: string): unknown {
	try {
		return JSON.parse(raw);
	} catch {
		return raw;
	}
}

function extractStoredCitations(
	message: ChatMessage,
): ReadonlyArray<CitationData> {
	if (!message.parts) return [];
	return message.parts.parts
		.filter((p): p is StoredCitationPart => p.kind === "citation")
		.map((p) => ({ rowLabel: p.row_label, colLabel: p.col_label }));
}

function toUIMessage(message: ChatMessage): UIMessage {
	const role = message.role === "user" ? "user" : "assistant";

	if (!message.parts) {
		return {
			id: message.id,
			role,
			parts: [{ type: "text", text: message.content } satisfies TextUIPart],
		};
	}

	const toolResults = new Map<string, { result: string; isError: boolean }>();
	for (const p of message.parts.parts) {
		if (p.kind === "tool_result") {
			toolResults.set(p.call_id, { result: p.result, isError: p.is_error });
		}
	}

	const uiParts: UIMessage["parts"] = [];

	for (const p of message.parts.parts) {
		if (p.kind === "text") {
			uiParts.push({ type: "text", text: p.content } satisfies TextUIPart);
		} else if (p.kind === "reasoning") {
			uiParts.push({
				type: "reasoning",
				text: p.content,
				state: "done",
			} satisfies ReasoningUIPart);
		} else if (p.kind === "tool_call") {
			const res = toolResults.get(p.call_id);
			let toolPart: DynamicToolUIPart;
			if (res) {
				if (res.isError) {
					toolPart = {
						type: "dynamic-tool",
						toolName: p.name,
						toolCallId: p.call_id,
						state: "output-error",
						input: safeParseJson(p.args),
						errorText: res.result,
					};
				} else {
					toolPart = {
						type: "dynamic-tool",
						toolName: p.name,
						toolCallId: p.call_id,
						state: "output-available",
						input: safeParseJson(p.args),
						output: safeParseJson(res.result),
					};
				}
			} else {
				toolPart = {
					type: "dynamic-tool",
					toolName: p.name,
					toolCallId: p.call_id,
					state: "input-available",
					input: safeParseJson(p.args),
				};
			}
			uiParts.push(toolPart);
		}
		// tool_result parts are consumed via toolResults map — skip standalone
	}

	return { id: message.id, role, parts: uiParts };
}

function AppChatPage() {
	const { chatId, documentId } = Route.useSearch();
	const navigate = Route.useNavigate();
	const queryClient = useQueryClient();
	const userId = useAuthedUserId();
	const selectedModel = useSelectedModel();
	const selectedModelRef = useRef(selectedModel);
	selectedModelRef.current = selectedModel;

	const seededChatIdRef = useRef<string | null>(null);

	const [citationsByMessageId, setCitationsByMessageId] = useState<
		ReadonlyMap<string, ReadonlyArray<CitationData>>
	>(() => new Map());

	const chatMessagesRef = useRef<typeof chat.messages>([]);

	const handleData = useCallback(
		(part: unknown) => {
			const partResult = ChatDataPartSchema.safeParse(part);
			if (!partResult.success) return;

			if (partResult.data.type === "data-conversation") {
				const dataResult = ConversationDataSchema.safeParse(
					partResult.data.data,
				);
				if (!dataResult.success || dataResult.data.conversationId === chatId) {
					return;
				}
				seededChatIdRef.current = dataResult.data.conversationId;
				void navigate({
					search: (prev) => ({
						...prev,
						chatId: dataResult.data.conversationId,
					}),
					replace: true,
				});
				return;
			}

			if (partResult.data.type === "data-citation") {
				const citationResult = CitationDataSchema.safeParse(
					partResult.data.data,
				);
				if (!citationResult.success) return;
				const messageId = findLastAssistantId(chatMessagesRef.current);
				if (!messageId) return;
				const citation = citationResult.data;
				setCitationsByMessageId((prev) => {
					const existing = prev.get(messageId) ?? [];
					const alreadyPresent = existing.some(
						(c) =>
							c.rowLabel === citation.rowLabel &&
							c.colLabel === citation.colLabel,
					);
					if (alreadyPresent) return prev;
					const next = new Map(prev);
					next.set(messageId, [...existing, citation]);
					return next;
				});
			}
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
		getModel: () => selectedModelRef.current,
		onData: handleData,
		onFinish: handleFinish,
	});

	const chatRef = useRef(chat);
	chatRef.current = chat;
	chatMessagesRef.current = chat.messages;

	useEffect(() => {
		const controls = {
			stop: () => chatRef.current.stop(),
			setMessages: (messages: UIMessage[]) =>
				chatRef.current.setMessages(messages),
		};
		registerChatResetControls(controls);
		return () => clearChatResetControls(controls);
	}, []);

	const closeOverlays = useCallback(() => {
		closeDocPicker();
		closeRightPanelSheet();
		closeSidebarDrawer();
	}, []);

	const messagesQuery = useChatMessages(chatId ?? null);

	useEffect(() => {
		if (!chatId || seededChatIdRef.current === chatId || !messagesQuery.data) {
			return;
		}
		const historical = new Map<string, ReadonlyArray<CitationData>>();
		for (const msg of messagesQuery.data.items) {
			const citations = extractStoredCitations(msg);
			if (citations.length > 0) {
				historical.set(msg.id, citations);
			}
		}
		setCitationsByMessageId(historical);
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

	const handleResetConversation = useCallback(() => {
		resetConversation({ navigate, closeOverlays }, { documentId: null });
	}, [navigate, closeOverlays]);

	return (
		<main className="flex h-full min-h-0 flex-col bg-background text-foreground">
			<header className="flex items-center justify-between gap-3 border-border border-b py-3 pr-6 pl-16 lg:pl-6">
				<div className="flex min-w-0 items-center gap-2">
					<div className="min-w-0">
						<h1 className="font-semibold text-base">
							<button
								type="button"
								onClick={handleResetConversation}
								data-testid="reset-logo-button"
								className="rounded-sm text-left hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
							>
								ConvFinQA
							</button>
						</h1>
						<p className="truncate text-muted-foreground text-xs">
							{documentId
								? `Pinned: ${documentId}`
								: "Pin a document to start asking questions."}
						</p>
					</div>
					{documentId ? (
						<button
							type="button"
							onClick={handleResetConversation}
							aria-label="Unpin document and start over"
							data-testid="unpin-button"
							className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
						>
							<X aria-hidden="true" className="size-4" />
						</button>
					) : null}
				</div>
				{documentId ? (
					<button
						type="button"
						onClick={openRightPanelSheet}
						data-testid="view-document-button"
						className="shrink-0 rounded-md border border-border bg-background px-2.5 py-1.5 text-foreground text-xs hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring lg:hidden"
					>
						View document
					</button>
				) : null}
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
						citationsByMessageId={citationsByMessageId}
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
				<div className="flex items-center justify-end">
					<ModelPicker />
				</div>
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

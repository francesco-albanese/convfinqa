import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useCallback } from "react";
import { Composer } from "@/components/Composer";
import { MessageList } from "@/components/MessageList";
import {
	type AppSearch,
	AppSearchSchema,
	ChatDataPartSchema,
	ConversationDataSchema,
} from "@/lib/chat/schemas";
import { useConvfinqaChat } from "@/lib/chat/useConvfinqaChat";

const STUB_USER_ID = "dev-user";

export const Route = createFileRoute("/_authed/app/")({
	validateSearch: (raw: Record<string, unknown>): AppSearch => {
		const parsed = AppSearchSchema.safeParse(raw);
		return parsed.success ? parsed.data : {};
	},
	component: AppChatPage,
});

function AppChatPage() {
	const { chatId, documentId } = Route.useSearch();
	const navigate = Route.useNavigate();
	const queryClient = useQueryClient();

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
		getUserId: () => STUB_USER_ID,
		getDocumentId: () => documentId ?? null,
		getConversationId: () => chatId ?? null,
		onData: handleData,
		onFinish: handleFinish,
	});

	const handleSend = (text: string) => {
		void chat.sendMessage({ text });
	};

	return (
		<main className="flex h-full min-h-0 flex-col bg-background text-foreground">
			<header className="border-border border-b px-6 py-3">
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
				<MessageList messages={chat.messages} status={chat.status} />
			</section>
			<section className="border-border border-t bg-background px-6 py-3">
				<Composer onSend={handleSend} disabled={!documentId} />
			</section>
		</main>
	);
}

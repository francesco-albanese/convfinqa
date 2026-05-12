import { type UseChatHelpers, useChat } from "@ai-sdk/react";
import type { ChatOnDataCallback, ChatOnFinishCallback, UIMessage } from "ai";
import { useMemo, useRef } from "react";
import { createChatTransport } from "@/lib/transport/createChatTransport";

export type UseConvfinqaChatOptions = {
	getUserId: () => string;
	getDocumentId: () => string | null;
	getConversationId: () => string | null;
	onData?: ChatOnDataCallback<UIMessage>;
	onFinish?: ChatOnFinishCallback<UIMessage>;
};

export function useConvfinqaChat(
	options: UseConvfinqaChatOptions,
): UseChatHelpers<UIMessage> {
	const optionsRef = useRef(options);
	optionsRef.current = options;

	const transport = useMemo(
		() =>
			createChatTransport({
				getUserId: () => optionsRef.current.getUserId(),
				getDocumentId: () => optionsRef.current.getDocumentId(),
				getConversationId: () => optionsRef.current.getConversationId(),
			}),
		[],
	);

	return useChat<UIMessage>({
		transport,
		onData: (part) => optionsRef.current.onData?.(part),
		onFinish: (event) => optionsRef.current.onFinish?.(event),
	});
}

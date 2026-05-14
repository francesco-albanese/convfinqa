import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import type { UIMessage } from "ai";
import { useCallback, useRef, useState } from "react";
import { useAuthedUserId } from "@/lib/auth/AuthProvider";
import { classifyStreamError } from "@/lib/chat/streamErrorClassifier";
import {
	type ChatMessageList,
	chatMessagesQueryKey,
	fetchChatMessages,
} from "@/lib/queries/chats";

const DEFAULT_MAX_POLL_ATTEMPTS = 10;
const DEFAULT_POLL_INTERVAL_MS = 500;

export type UseStreamErrorRetryOptions = {
	chat: {
		error: Error | undefined;
		messages: UIMessage[];
		sendMessage: (message: { text: string }) => Promise<void>;
		clearError: () => void;
	};
	chatId: string | null;
	maxPollAttempts?: number;
	pollIntervalMs?: number;
};

export type UseStreamErrorRetry = {
	retry: () => Promise<void>;
	dismiss: () => void;
	isRetrying: boolean;
};

function getLastUserText(messages: UIMessage[]): string | null {
	for (let i = messages.length - 1; i >= 0; i--) {
		const message = messages[i];
		if (message?.role !== "user") continue;
		const text = message.parts
			.flatMap((part) => (part.type === "text" ? [part.text] : []))
			.join("");
		return text.length > 0 ? text : null;
	}
	return null;
}

async function waitForPreviousResponse(
	queryClient: QueryClient,
	chatId: string,
	userId: string,
	maxAttempts: number,
	intervalMs: number,
): Promise<void> {
	const queryKey = chatMessagesQueryKey(chatId);
	const initial = queryClient.getQueryData<ChatMessageList>(queryKey);
	const initialCount = initial?.items.length ?? 0;

	for (let attempt = 0; attempt < maxAttempts; attempt++) {
		const fresh = await queryClient.fetchQuery({
			queryKey,
			queryFn: () => fetchChatMessages(chatId, userId),
			staleTime: 0,
		});
		if (fresh.items.length > initialCount) return;
		if (attempt < maxAttempts - 1) {
			await new Promise((resolve) => setTimeout(resolve, intervalMs));
		}
	}
}

export function useStreamErrorRetry({
	chat,
	chatId,
	maxPollAttempts = DEFAULT_MAX_POLL_ATTEMPTS,
	pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
}: UseStreamErrorRetryOptions): UseStreamErrorRetry {
	const queryClient = useQueryClient();
	const userId = useAuthedUserId();
	const [isRetrying, setIsRetrying] = useState(false);
	const inFlightRef = useRef(false);

	const dismiss = useCallback(() => {
		chat.clearError();
	}, [chat]);

	const retry = useCallback(async () => {
		if (inFlightRef.current) return;
		const lastUserText = getLastUserText(chat.messages);
		if (!lastUserText) return;

		const errorClass = classifyStreamError(chat.error);

		inFlightRef.current = true;
		setIsRetrying(true);
		try {
			if (errorClass === "concurrent" && chatId) {
				await waitForPreviousResponse(
					queryClient,
					chatId,
					userId,
					maxPollAttempts,
					pollIntervalMs,
				);
			}
			chat.clearError();
			await chat.sendMessage({ text: lastUserText });
		} finally {
			inFlightRef.current = false;
			setIsRetrying(false);
		}
	}, [chat, chatId, maxPollAttempts, pollIntervalMs, queryClient, userId]);

	return { retry, dismiss, isRetrying };
}

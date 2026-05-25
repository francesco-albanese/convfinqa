import type { ChatStatus, UIMessage } from "ai";
import { MessageBubble } from "@/components/MessageBubble";
import type { CitationData } from "@/lib/chat/schemas";

type MessageListProps = {
	messages: UIMessage[];
	status: ChatStatus;
	stoppedIds?: ReadonlySet<string>;
	citationsByMessageId?: ReadonlyMap<string, ReadonlyArray<CitationData>>;
};

export function MessageList({
	messages,
	status,
	stoppedIds,
	citationsByMessageId,
}: MessageListProps) {
	const lastAssistantIndex = findLastAssistantIndex(messages);
	const inFlight = status === "streaming" || status === "submitted";

	return (
		<ol className="flex flex-col gap-4">
			{messages.map((message, index) => (
				<li key={message.id}>
					<MessageBubble
						message={message}
						showCursor={inFlight && index === lastAssistantIndex}
						stopped={
							message.role === "assistant" &&
							stoppedIds?.has(message.id) === true
						}
						citations={citationsByMessageId?.get(message.id)}
					/>
				</li>
			))}
		</ol>
	);
}

function findLastAssistantIndex(messages: UIMessage[]): number {
	for (let i = messages.length - 1; i >= 0; i--) {
		if (messages[i]?.role === "assistant") return i;
	}
	return -1;
}

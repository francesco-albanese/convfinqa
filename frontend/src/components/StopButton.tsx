import type { ChatStatus } from "ai";
import { Square } from "lucide-react";
import { cn } from "@/lib/utils";

type StopButtonProps = {
	status: ChatStatus;
	stop: () => void | Promise<void>;
	streamingMessageId: string | null;
	onStopped: (messageId: string) => void;
	className?: string;
};

export function StopButton({
	status,
	stop,
	streamingMessageId,
	onStopped,
	className,
}: StopButtonProps) {
	const isInFlight = status === "streaming" || status === "submitted";
	if (!isInFlight) return null;

	const handleClick = () => {
		if (streamingMessageId) {
			onStopped(streamingMessageId);
		}
		void stop();
	};

	return (
		<button
			type="button"
			onClick={handleClick}
			aria-label="Stop generating"
			className={cn(
				"inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-3 text-xs font-medium text-foreground",
				"hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
				className,
			)}
		>
			<Square aria-hidden="true" className="size-3.5 fill-current" />
			Stop
		</button>
	);
}

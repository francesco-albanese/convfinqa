import { RotateCcw, X } from "lucide-react";
import {
	classifyStreamError,
	type StreamErrorClass,
} from "@/lib/chat/streamErrorClassifier";
import { cn } from "@/lib/utils";

type StreamErrorBannerProps = {
	error: Error | undefined;
	onRetry: () => void | Promise<void>;
	onDismiss: () => void;
	isRetrying?: boolean;
	className?: string;
};

const COPY: Record<StreamErrorClass, { title: string; detail: string }> = {
	concurrent: {
		title: "Another response is in progress",
		detail:
			"Wait a moment — retrying will resend your message once the current response finishes.",
	},
	network: {
		title: "Connection lost",
		detail: "We couldn't reach the server. Check your connection and retry.",
	},
	server: {
		title: "Server error",
		detail: "Something went wrong on our side. Retry in a moment.",
	},
	unknown: {
		title: "Something went wrong",
		detail: "The response failed. Retry your last message.",
	},
};

export function StreamErrorBanner({
	error,
	onRetry,
	onDismiss,
	isRetrying = false,
	className,
}: StreamErrorBannerProps) {
	const errorClass = classifyStreamError(error);
	if (!errorClass) return null;

	const { title, detail } = COPY[errorClass];

	return (
		<div
			role="alert"
			data-testid="stream-error-banner"
			data-error-class={errorClass}
			className={cn(
				"flex items-start gap-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-destructive text-sm",
				className,
			)}
		>
			<div className="flex-1">
				<p className="font-medium">{title}</p>
				<p className="text-destructive/80 text-xs">{detail}</p>
			</div>
			<button
				type="button"
				onClick={() => void onRetry()}
				disabled={isRetrying}
				className="inline-flex h-7 items-center gap-1.5 rounded-md border border-destructive/40 bg-background px-2.5 font-medium text-foreground text-xs hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-60"
			>
				<RotateCcw aria-hidden="true" className="size-3.5" />
				{isRetrying ? "Retrying…" : "Retry"}
			</button>
			<button
				type="button"
				onClick={onDismiss}
				aria-label="Dismiss error"
				className="inline-flex h-7 w-7 items-center justify-center rounded-md text-destructive hover:bg-destructive/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
			>
				<X aria-hidden="true" className="size-4" />
			</button>
		</div>
	);
}

import { useEffect, useId, useState } from "react";
import { cn } from "@/lib/utils";

type ThinkingDisclosureProps = {
	text: string;
	isStreaming?: boolean;
};

export function ThinkingDisclosure({
	text,
	isStreaming = false,
}: ThinkingDisclosureProps) {
	const [open, setOpen] = useState(isStreaming);
	const panelId = useId();

	useEffect(() => {
		if (!isStreaming) {
			setOpen(false);
		}
	}, [isStreaming]);

	return (
		<div className="mb-2 rounded-lg border border-border/50 bg-muted/30 text-sm">
			<button
				type="button"
				onClick={() => setOpen((o) => !o)}
				className={cn(
					"flex w-full items-center gap-2 px-3 py-2 text-left",
					"text-muted-foreground text-xs hover:text-foreground",
					"focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
				)}
				aria-expanded={open}
				aria-controls={panelId}
			>
				<span
					aria-hidden="true"
					className={cn(
						"transition-transform",
						open ? "rotate-90" : "rotate-0",
					)}
				>
					▶
				</span>
				<span className="font-medium">Thinking</span>
				{isStreaming && (
					<span aria-hidden="true" className="ml-1 animate-pulse">
						…
					</span>
				)}
			</button>
			<div
				id={panelId}
				hidden={!open}
				className="border-t border-border/50 px-3 py-2 font-mono text-muted-foreground text-xs leading-relaxed whitespace-pre-wrap"
			>
				{text}
			</div>
		</div>
	);
}

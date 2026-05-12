import { Pin } from "lucide-react";

type EmptyStateProps = {
	onPinDocument?: () => void;
};

export function EmptyState({ onPinDocument }: EmptyStateProps) {
	return (
		<section
			aria-label="Empty conversation"
			data-testid="empty-state"
			className="flex h-full flex-col items-center justify-center px-6 text-center"
		>
			<p className="text-muted-foreground text-xs uppercase tracking-widest">
				no document pinned
			</p>
			<h2 className="mt-3 font-semibold text-2xl text-foreground tracking-tight">
				Pin a document to start chatting
			</h2>
			<p className="mt-2 max-w-md text-muted-foreground text-sm">
				Conversations in ConvFinQA are per document. Open the command palette to
				search the library.
			</p>
			{onPinDocument ? (
				<button
					type="button"
					onClick={onPinDocument}
					className="mt-6 inline-flex h-9 items-center gap-2 rounded-md bg-primary px-3 font-medium text-primary-foreground text-sm hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
				>
					<Pin aria-hidden="true" className="size-4" />
					Pin a document
				</button>
			) : null}
		</section>
	);
}

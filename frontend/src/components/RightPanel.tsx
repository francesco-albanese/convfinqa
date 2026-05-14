import { Clipboard, ClipboardCheck, FileText, X } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { DocTable } from "@/components/DocTable";
import { ResizableSplit } from "@/components/ResizableSplit";
import { type Document, useDocument } from "@/lib/queries/documents";
import { rowMajorToCsv } from "@/lib/transforms/rowMajorToCsv";
import {
	type RowMajorTable,
	tableToRowMajor,
} from "@/lib/transforms/tableToRowMajor";
import { cn } from "@/lib/utils";

export type RightPanelProps = {
	documentId: string;
	onChangeDocument: () => void;
	onClose?: () => void;
	className?: string;
	modal?: boolean;
	ref?: React.Ref<HTMLElement>;
};

export function RightPanel({
	documentId,
	onChangeDocument,
	onClose,
	className,
	modal = false,
	ref,
}: RightPanelProps) {
	const { data: document, isLoading, isError } = useDocument(documentId);

	const table = useMemo<RowMajorTable | null>(() => {
		if (!document?.table_data) return null;
		return tableToRowMajor(document.table_data, document.column_order);
	}, [document?.table_data, document?.column_order]);

	const dialogProps: Record<string, unknown> = modal
		? { role: "dialog", "aria-modal": true, tabIndex: -1 }
		: {};

	return (
		<aside
			ref={ref}
			aria-label="Pinned document"
			data-testid="right-panel"
			{...dialogProps}
			className={cn("h-full bg-card", className)}
		>
			<ResizableSplit className="h-full">
				<div className="flex h-full flex-col overflow-hidden">
					<RightPanelHeader
						document={document}
						documentId={documentId}
						onChangeDocument={onChangeDocument}
						onClose={onClose}
					/>
					<div className="flex-1 overflow-y-auto px-4 py-4">
						<RightPanelBody
							isLoading={isLoading}
							isError={isError}
							document={document}
							table={table}
						/>
					</div>
				</div>
			</ResizableSplit>
		</aside>
	);
}

type RightPanelHeaderProps = {
	document: Document | undefined;
	documentId: string;
	onChangeDocument: () => void;
	onClose?: () => void;
};

function RightPanelHeader({
	document,
	documentId,
	onChangeDocument,
	onClose,
}: RightPanelHeaderProps) {
	const displayTitle = document?.title ?? documentId;
	return (
		<header
			data-testid="right-panel-header"
			className="flex items-center justify-between gap-3 border-border border-b px-4 py-3"
		>
			<div className="flex min-w-0 items-center gap-2">
				<FileText
					aria-hidden="true"
					className="size-4 shrink-0 text-muted-foreground"
				/>
				<h2 className="truncate font-medium text-foreground text-sm">
					{displayTitle}
				</h2>
			</div>
			<div className="flex shrink-0 items-center gap-2">
				<button
					type="button"
					onClick={onChangeDocument}
					data-testid="right-panel-change-document"
					className="rounded-md border border-border bg-background px-2.5 py-1 text-foreground text-xs hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
				>
					Change document
				</button>
				{onClose ? (
					<button
						type="button"
						onClick={onClose}
						aria-label="Close document panel"
						data-testid="right-panel-close"
						data-modal-initial-focus
						className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring lg:hidden"
					>
						<X aria-hidden="true" className="size-3.5" />
					</button>
				) : null}
			</div>
		</header>
	);
}

type RightPanelBodyProps = {
	isLoading: boolean;
	isError: boolean;
	document: Document | undefined;
	table: RowMajorTable | null;
};

function RightPanelBody({
	isLoading,
	isError,
	document,
	table,
}: RightPanelBodyProps) {
	if (isLoading) {
		return (
			<p
				role="status"
				aria-live="polite"
				className="text-muted-foreground text-sm"
			>
				Loading document…
			</p>
		);
	}
	if (isError || !document) {
		return (
			<p
				role="alert"
				className="text-destructive text-sm"
				data-testid="right-panel-error"
			>
				Could not load the pinned document.
			</p>
		);
	}
	return (
		<div className="flex flex-col gap-4">
			{document.pre_text ? (
				<NarrativeText testId="right-panel-pre-text" text={document.pre_text} />
			) : null}
			{table ? (
				<>
					<DocTable table={table} />
					<CopyAsCsvButton table={table} />
				</>
			) : (
				<p
					data-testid="right-panel-empty-table"
					className="text-muted-foreground text-sm"
				>
					This document has no structured table.
				</p>
			)}
			{document.post_text ? (
				<NarrativeText
					testId="right-panel-post-text"
					text={document.post_text}
				/>
			) : null}
		</div>
	);
}

type NarrativeTextProps = {
	testId: string;
	text: string;
};

function NarrativeText({ testId, text }: NarrativeTextProps) {
	return (
		<p
			data-testid={testId}
			className="whitespace-pre-wrap text-muted-foreground text-sm leading-relaxed"
		>
			{text}
		</p>
	);
}

const COPY_FEEDBACK_MS = 1500;

type CopyAsCsvButtonProps = {
	table: RowMajorTable;
};

type CopyStatus = "idle" | "copied" | "failed";

function CopyAsCsvButton({ table }: CopyAsCsvButtonProps) {
	const [status, setStatus] = useState<CopyStatus>("idle");

	const handleCopy = useCallback(async () => {
		const csv = rowMajorToCsv(table);
		try {
			await navigator.clipboard.writeText(csv);
			setStatus("copied");
		} catch {
			setStatus("failed");
		}
		window.setTimeout(() => setStatus("idle"), COPY_FEEDBACK_MS);
	}, [table]);

	const label =
		status === "copied"
			? "Copied"
			: status === "failed"
				? "Copy failed"
				: "Copy as CSV";

	return (
		<div className="flex justify-end">
			<button
				type="button"
				onClick={handleCopy}
				data-testid="right-panel-copy-csv"
				data-status={status}
				className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-foreground text-xs hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring data-[status=failed]:text-destructive"
			>
				{status === "copied" ? (
					<ClipboardCheck aria-hidden="true" className="size-3.5" />
				) : (
					<Clipboard aria-hidden="true" className="size-3.5" />
				)}
				{label}
			</button>
		</div>
	);
}

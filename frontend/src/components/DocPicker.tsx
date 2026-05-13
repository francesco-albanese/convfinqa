import { useDebouncedValue } from "@tanstack/react-pacer";
import { useVirtualizer } from "@tanstack/react-virtual";
import { FileText, Loader2, Search } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Slider } from "@/components/ui/slider";
import { type DocumentSummary, useDocumentList } from "@/lib/queries/documents";

const DEFAULT_YEAR_MIN = 2000;
const DEFAULT_YEAR_MAX = 2025;
const SEARCH_DEBOUNCE_MS = 200;
const ROW_HEIGHT_PX = 56;
const LIST_HEIGHT_PX = 360;

export type DocPickerProps = {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onSelect: (documentId: string) => void;
};

export function DocPicker({ open, onOpenChange, onSelect }: DocPickerProps) {
	const [query, setQuery] = useState("");
	const [years, setYears] = useState<[number, number]>([
		DEFAULT_YEAR_MIN,
		DEFAULT_YEAR_MAX,
	]);
	const [debouncedQuery] = useDebouncedValue(query, {
		wait: SEARCH_DEBOUNCE_MS,
	});
	const searchInputId = useId();

	useEffect(() => {
		if (!open) {
			setQuery("");
			setYears([DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX]);
		}
	}, [open]);

	const isDefaultYears =
		years[0] === DEFAULT_YEAR_MIN && years[1] === DEFAULT_YEAR_MAX;

	const { data, isLoading, isFetching, hasNextPage, fetchNextPage } =
		useDocumentList({
			q: debouncedQuery,
			yearMin: isDefaultYears ? undefined : years[0],
			yearMax: isDefaultYears ? undefined : years[1],
		});

	const items = useMemo<DocumentSummary[]>(
		() => data?.pages.flatMap((page) => page.items) ?? [],
		[data?.pages],
	);

	const handleSelect = (id: string) => {
		onSelect(id);
		onOpenChange(false);
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent data-testid="doc-picker">
				<DialogHeader>
					<DialogTitle>Library</DialogTitle>
					<DialogDescription>
						Search across the document corpus by ticker, title, or topic.
					</DialogDescription>
				</DialogHeader>

				<div className="px-5">
					<label htmlFor={searchInputId} className="sr-only">
						Search documents
					</label>
					<div className="relative">
						<Search
							aria-hidden="true"
							className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
						/>
						<input
							id={searchInputId}
							type="search"
							value={query}
							onChange={(event) => setQuery(event.target.value)}
							placeholder="Search by ticker, title, or topic"
							className="h-10 w-full rounded-md border border-border bg-input pr-10 pl-9 text-foreground text-sm placeholder:text-muted-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
							autoComplete="off"
						/>
						{isFetching ? (
							<Loader2
								aria-label="Loading"
								className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground"
							/>
						) : null}
					</div>
				</div>

				<div className="px-5">
					<div className="flex items-center justify-between text-muted-foreground text-xs">
						<span>Year range</span>
						<span
							aria-live="polite"
							className="font-medium text-foreground tabular-nums"
						>
							{years[0]} – {years[1]}
						</span>
					</div>
					<Slider
						aria-label="Year range"
						className="mt-2"
						min={DEFAULT_YEAR_MIN}
						max={DEFAULT_YEAR_MAX}
						step={1}
						value={years}
						onValueChange={(value: number[]) => {
							const [lower, upper] = value;
							if (lower !== undefined && upper !== undefined) {
								setYears([lower, upper]);
							}
						}}
					/>
				</div>

				<DocPickerResults
					items={items}
					isLoading={isLoading}
					hasNextPage={hasNextPage}
					onFetchNextPage={() => {
						void fetchNextPage();
					}}
					onSelect={handleSelect}
				/>
			</DialogContent>
		</Dialog>
	);
}

type DocPickerResultsProps = {
	items: DocumentSummary[];
	isLoading: boolean;
	hasNextPage: boolean;
	onFetchNextPage: () => void;
	onSelect: (id: string) => void;
};

function DocPickerResults({
	items,
	isLoading,
	hasNextPage,
	onFetchNextPage,
	onSelect,
}: DocPickerResultsProps) {
	const scrollRef = useRef<HTMLDivElement>(null);
	const virtualizer = useVirtualizer({
		count: items.length,
		getScrollElement: () => scrollRef.current,
		estimateSize: () => ROW_HEIGHT_PX,
		overscan: 6,
	});

	const virtualItems = virtualizer.getVirtualItems();
	// jsdom returns an empty virtualItems array because ResizeObserver is shimmed
	// to a no-op (see src/test/setup.ts), so the scroll element measures 0×0.
	// Fall back to rendering every row so tests can still assert on the list.
	const renderedItems =
		virtualItems.length === 0 && items.length > 0
			? items.map((_, index) => ({
					index,
					start: index * ROW_HEIGHT_PX,
					size: ROW_HEIGHT_PX,
					key: index,
				}))
			: virtualItems;

	if (isLoading) {
		return (
			<div
				role="status"
				aria-live="polite"
				className="px-5 py-6 text-center text-muted-foreground text-sm"
			>
				Loading documents…
			</div>
		);
	}

	if (items.length === 0) {
		return (
			<div
				role="status"
				aria-live="polite"
				className="px-5 py-6 text-center text-muted-foreground text-sm"
			>
				No documents match your filters.
			</div>
		);
	}

	return (
		<div
			ref={scrollRef}
			role="listbox"
			aria-label="Document results"
			className="overflow-y-auto px-2 pb-4"
			style={{ height: `${LIST_HEIGHT_PX}px` }}
		>
			<ul
				className="relative w-full"
				style={{
					height: `${virtualizer.getTotalSize() || items.length * ROW_HEIGHT_PX}px`,
				}}
			>
				{renderedItems.map((virtualRow) => {
					const item = items[virtualRow.index];
					if (!item) return null;
					return (
						<li
							key={item.id}
							data-index={virtualRow.index}
							className="absolute inset-x-0"
							style={{
								transform: `translateY(${virtualRow.start}px)`,
								height: `${virtualRow.size}px`,
							}}
						>
							<button
								type="button"
								role="option"
								aria-selected="false"
								onClick={() => onSelect(item.id)}
								data-testid="doc-picker-result"
								data-doc-id={item.id}
								className="flex h-full w-full items-center gap-3 rounded-md px-3 text-left text-foreground text-sm hover:bg-secondary focus-visible:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
							>
								<FileText
									aria-hidden="true"
									className="size-4 shrink-0 text-muted-foreground"
								/>
								<span className="min-w-0 flex-1 truncate">
									{item.title ?? item.id}
								</span>
								<span className="shrink-0 text-muted-foreground text-xs tabular-nums">
									{item.ticker ?? "—"}
									{item.year ? ` · ${item.year}` : ""}
								</span>
							</button>
						</li>
					);
				})}
			</ul>
			{hasNextPage ? (
				<div className="flex justify-center py-3">
					<button
						type="button"
						onClick={onFetchNextPage}
						className="rounded-md border border-border px-3 py-1.5 text-foreground text-xs hover:bg-secondary"
					>
						Load more
					</button>
				</div>
			) : null}
		</div>
	);
}

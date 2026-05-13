import {
	type KeyboardEvent as ReactKeyboardEvent,
	type PointerEvent as ReactPointerEvent,
	useCallback,
	useEffect,
	useRef,
} from "react";
import {
	clampPanelWidth,
	PANEL_WIDTH_MAX_FRACTION,
	PANEL_WIDTH_MIN,
	resetPanelWidth,
	setPanelWidth,
	usePanelWidth,
} from "@/lib/ui/panelWidthStore";
import { cn } from "@/lib/utils";

export type ResizableSplitProps = {
	children: React.ReactNode;
	className?: string;
};

export function ResizableSplit({ children, className }: ResizableSplitProps) {
	const width = usePanelWidth();
	const draggingRef = useRef(false);
	const viewportMax =
		typeof window === "undefined"
			? PANEL_WIDTH_MIN
			: Math.round(window.innerWidth * PANEL_WIDTH_MAX_FRACTION);

	useEffect(() => {
		function handleMove(event: PointerEvent) {
			if (!draggingRef.current) return;
			const next = clampPanelWidth(
				window.innerWidth - event.clientX,
				window.innerWidth,
			);
			setPanelWidth(next);
		}
		function handleUp() {
			draggingRef.current = false;
			document.body.style.removeProperty("cursor");
			document.body.style.removeProperty("user-select");
		}
		window.addEventListener("pointermove", handleMove);
		window.addEventListener("pointerup", handleUp);
		window.addEventListener("pointercancel", handleUp);
		return () => {
			window.removeEventListener("pointermove", handleMove);
			window.removeEventListener("pointerup", handleUp);
			window.removeEventListener("pointercancel", handleUp);
			if (draggingRef.current) {
				draggingRef.current = false;
				document.body.style.removeProperty("cursor");
				document.body.style.removeProperty("user-select");
			}
		};
	}, []);

	const handlePointerDown = useCallback(
		(event: ReactPointerEvent<HTMLDivElement>) => {
			event.preventDefault();
			draggingRef.current = true;
			document.body.style.cursor = "col-resize";
			document.body.style.userSelect = "none";
		},
		[],
	);

	const handleDoubleClick = useCallback(() => {
		resetPanelWidth();
	}, []);

	const panelWidthAtRender = useRef(width);
	panelWidthAtRender.current = width;

	const handleKeyDown = useCallback(
		(event: ReactKeyboardEvent<HTMLDivElement>) => {
			const max = window.innerWidth * PANEL_WIDTH_MAX_FRACTION;
			const step = event.shiftKey ? 32 : 8;
			const current = panelWidthAtRender.current;
			let next: number | null = null;
			if (event.key === "ArrowLeft") next = current + step;
			else if (event.key === "ArrowRight") next = current - step;
			else if (event.key === "Home") next = PANEL_WIDTH_MIN;
			else if (event.key === "End") next = max;
			if (next === null) return;
			event.preventDefault();
			setPanelWidth(clampPanelWidth(next, window.innerWidth));
		},
		[],
	);

	return (
		<div
			data-testid="resizable-split"
			className={cn("relative flex h-full", className)}
			style={{ width: `${width}px` }}
		>
			{/* biome-ignore lint/a11y/useSemanticElements: Biome cannot infer that role=separator is the semantic element for an interactive splitter; <hr> is non-interactive. */}
			<div
				role="separator"
				aria-orientation="vertical"
				aria-label="Resize panel"
				aria-valuenow={Math.round(width)}
				aria-valuemin={PANEL_WIDTH_MIN}
				aria-valuemax={viewportMax}
				data-testid="resize-handle"
				onPointerDown={handlePointerDown}
				onDoubleClick={handleDoubleClick}
				onKeyDown={handleKeyDown}
				className="absolute top-0 bottom-0 left-0 z-10 w-1 -translate-x-1/2 cursor-col-resize bg-transparent hover:bg-border focus-visible:bg-border"
				tabIndex={0}
			/>
			<div className="flex h-full min-w-0 flex-1 flex-col overflow-hidden">
				{children}
			</div>
		</div>
	);
}

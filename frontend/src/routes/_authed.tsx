import { createFileRoute, Outlet } from "@tanstack/react-router";
import { type LayoutSearch, LayoutSearchSchema } from "@/lib/layout/schemas";

export const Route = createFileRoute("/_authed")({
	validateSearch: (raw: Record<string, unknown>): LayoutSearch => {
		const parsed = LayoutSearchSchema.safeParse(raw);
		return parsed.success ? parsed.data : {};
	},
	component: AuthedLayout,
});

function AuthedLayout() {
	const { documentId } = Route.useSearch();
	const isRightPanelOpen = Boolean(documentId);

	return (
		<div
			data-testid="authed-shell"
			data-right-panel={isRightPanelOpen ? "open" : "closed"}
			className={
				isRightPanelOpen
					? "grid h-screen w-screen overflow-hidden bg-background text-foreground grid-cols-[280px_minmax(0,1fr)_380px]"
					: "grid h-screen w-screen overflow-hidden bg-background text-foreground grid-cols-[280px_minmax(0,1fr)_0px]"
			}
		>
			<aside
				aria-label="Sidebar"
				className="h-full border-border border-r bg-card"
			/>
			<div className="flex h-full min-w-0 flex-col overflow-hidden">
				<Outlet />
			</div>
			{isRightPanelOpen ? (
				<aside
					aria-label="Pinned document"
					data-testid="right-panel"
					className="h-full border-border border-l bg-card"
				/>
			) : null}
		</div>
	);
}

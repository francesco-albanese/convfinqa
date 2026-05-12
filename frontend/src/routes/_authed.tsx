import { createFileRoute, Outlet } from "@tanstack/react-router";
import { type LayoutSearch, LayoutSearchSchema } from "@/lib/layout/schemas";
import { useSidebarCollapsed } from "@/lib/ui/sidebarStore";

const SIDEBAR_WIDTH_EXPANDED = "280px";
const SIDEBAR_WIDTH_COLLAPSED = "64px";
const RIGHT_PANEL_WIDTH = "380px";

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
	const collapsed = useSidebarCollapsed();

	const sidebarWidth = collapsed
		? SIDEBAR_WIDTH_COLLAPSED
		: SIDEBAR_WIDTH_EXPANDED;
	const rightWidth = isRightPanelOpen ? RIGHT_PANEL_WIDTH : "0px";

	return (
		<div
			data-testid="authed-shell"
			data-right-panel={isRightPanelOpen ? "open" : "closed"}
			data-sidebar={collapsed ? "collapsed" : "expanded"}
			className="grid h-screen w-screen overflow-hidden bg-background text-foreground"
			style={{
				gridTemplateColumns: `${sidebarWidth} minmax(0,1fr) ${rightWidth}`,
			}}
		>
			<aside
				aria-label="Sidebar"
				data-testid="sidebar"
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

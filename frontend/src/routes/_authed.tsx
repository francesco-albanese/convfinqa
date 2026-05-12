import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useCallback } from "react";
import { Sidebar } from "@/components/Sidebar";
import { STUB_USER_ID } from "@/lib/auth/stubUser";
import { type LayoutSearch, LayoutSearchSchema } from "@/lib/layout/schemas";
import { toggleSidebar, useSidebarCollapsed } from "@/lib/ui/sidebarStore";

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
	const navigate = useNavigate();

	const sidebarWidth = collapsed
		? SIDEBAR_WIDTH_COLLAPSED
		: SIDEBAR_WIDTH_EXPANDED;
	const rightWidth = isRightPanelOpen ? RIGHT_PANEL_WIDTH : "0px";

	const handleNewConversation = useCallback(() => {
		void navigate({
			to: "/app",
			search: (prev) => ({ ...prev, chatId: undefined }),
		});
	}, [navigate]);

	const handleSignOut = useCallback(() => {
		console.warn("signOut: stub — wired in convfinqa-ebw");
	}, []);

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
			<Sidebar
				chats={[]}
				collapsed={collapsed}
				userId={STUB_USER_ID}
				onToggleCollapse={toggleSidebar}
				onNewConversation={handleNewConversation}
				onSignOut={handleSignOut}
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

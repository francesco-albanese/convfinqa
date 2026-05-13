import {
	createFileRoute,
	Outlet,
	redirect,
	useNavigate,
} from "@tanstack/react-router";
import { useCallback } from "react";
import { DocPicker } from "@/components/DocPicker";
import { Sidebar } from "@/components/Sidebar";
import {
	readPersistedAuthUserId,
	useAuthedUserId,
} from "@/lib/auth/AuthProvider";
import { type LayoutSearch, LayoutSearchSchema } from "@/lib/layout/schemas";
import {
	openDocPicker,
	setDocPickerOpen,
	useDocPickerOpen,
} from "@/lib/ui/docPickerStore";
import { toggleSidebar, useSidebarCollapsed } from "@/lib/ui/sidebarStore";

const SIDEBAR_WIDTH_EXPANDED = "280px";
const SIDEBAR_WIDTH_COLLAPSED = "64px";
const RIGHT_PANEL_WIDTH = "380px";

export const Route = createFileRoute("/_authed")({
	beforeLoad: () => {
		if (readPersistedAuthUserId() === null) {
			throw redirect({ to: "/sign-in" });
		}
	},
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
	const pickerOpen = useDocPickerOpen();
	const navigate = useNavigate();
	const userId = useAuthedUserId();

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
		console.warn("signOut: stub — wired in convfinqa-ebw.5");
	}, []);

	const handlePickDocumentSelect = useCallback(
		(id: string) => {
			void navigate({
				to: "/app",
				search: (prev) => ({ ...prev, documentId: id }),
			});
		},
		[navigate],
	);

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
				userId={userId}
				onToggleCollapse={toggleSidebar}
				onNewConversation={handleNewConversation}
				onPickDocument={openDocPicker}
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
			<DocPicker
				open={pickerOpen}
				onOpenChange={setDocPickerOpen}
				onSelect={handlePickDocumentSelect}
			/>
		</div>
	);
}

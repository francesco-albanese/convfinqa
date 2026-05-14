import {
	createFileRoute,
	Outlet,
	redirect,
	useNavigate,
} from "@tanstack/react-router";
import { useCallback, useEffect } from "react";
import { DocPicker } from "@/components/DocPicker";
import { RightPanel } from "@/components/RightPanel";
import { Sidebar } from "@/components/Sidebar";
import { readPersistedAuthUserId, useAuth } from "@/lib/auth/AuthProvider";
import { type LayoutSearch, LayoutSearchSchema } from "@/lib/layout/schemas";
import {
	openDocPicker,
	setDocPickerOpen,
	useDocPickerOpen,
} from "@/lib/ui/docPickerStore";
import { toggleSidebar, useSidebarCollapsed } from "@/lib/ui/sidebarStore";

const SIDEBAR_WIDTH_EXPANDED = "280px";
const SIDEBAR_WIDTH_COLLAPSED = "64px";

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
	const pinnedDocumentId =
		typeof documentId === "string" && documentId.length > 0 ? documentId : null;
	const isRightPanelOpen = pinnedDocumentId !== null;
	const collapsed = useSidebarCollapsed();
	const pickerOpen = useDocPickerOpen();
	const navigate = useNavigate();
	const { userId, signOut } = useAuth();

	useEffect(() => {
		if (userId === null) {
			void navigate({ to: "/sign-in", replace: true });
		}
	}, [userId, navigate]);

	const handleNewConversation = useCallback(() => {
		void navigate({
			to: "/app",
			search: (prev) => ({ ...prev, chatId: undefined }),
		});
	}, [navigate]);

	const handleSignOut = useCallback(() => {
		signOut();
	}, [signOut]);

	const handlePickDocumentSelect = useCallback(
		(id: string) => {
			void navigate({
				to: "/app",
				search: (prev) => ({ ...prev, documentId: id }),
			});
		},
		[navigate],
	);

	const handleSelectChat = useCallback(
		(chatId: string, documentId: string) => {
			void navigate({
				to: "/app",
				search: (prev) => ({ ...prev, chatId, documentId }),
			});
		},
		[navigate],
	);

	if (userId === null) {
		return null;
	}

	const sidebarWidth = collapsed
		? SIDEBAR_WIDTH_COLLAPSED
		: SIDEBAR_WIDTH_EXPANDED;
	const rightWidth = isRightPanelOpen ? "auto" : "0px";

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
				collapsed={collapsed}
				userId={userId}
				onToggleCollapse={toggleSidebar}
				onNewConversation={handleNewConversation}
				onPickDocument={openDocPicker}
				onSelectChat={handleSelectChat}
				onSignOut={handleSignOut}
			/>
			<div className="flex h-full min-w-0 flex-col overflow-hidden">
				<Outlet />
			</div>
			{pinnedDocumentId !== null ? (
				<RightPanel
					documentId={pinnedDocumentId}
					onChangeDocument={openDocPicker}
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

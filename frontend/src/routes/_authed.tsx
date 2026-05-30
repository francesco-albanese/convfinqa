import {
	createFileRoute,
	Outlet,
	useNavigate,
	useSearch,
} from "@tanstack/react-router";
import { Menu } from "lucide-react";
import { useCallback, useEffect, useRef } from "react";
import { AuthLoadingShell } from "@/components/AuthLoadingShell";
import { DocPicker } from "@/components/DocPicker";
import { RightPanel } from "@/components/RightPanel";
import { Sidebar } from "@/components/Sidebar";
import { useAuth } from "@/lib/auth/AuthProvider";
import { resetConversation } from "@/lib/chat/conversationReset";
import { type LayoutSearch, LayoutSearchSchema } from "@/lib/layout/schemas";
import { useDeleteConversation } from "@/lib/queries/chats";
import {
	closeDocPicker,
	openDocPicker,
	setDocPickerOpen,
	useDocPickerOpen,
} from "@/lib/ui/docPickerStore";
import {
	closeRightPanelSheet,
	closeSidebarDrawer,
	openSidebarDrawer,
	useRightPanelSheetOpen,
	useSidebarDrawerOpen,
} from "@/lib/ui/responsiveStore";
import { toggleSidebar, useSidebarCollapsed } from "@/lib/ui/sidebarStore";
import { useIsBelowLg } from "@/lib/ui/useIsBelowLg";
import { useModalDialog } from "@/lib/ui/useModalDialog";
import { cn } from "@/lib/utils";

const SIDEBAR_WIDTH_EXPANDED = "280px";
const SIDEBAR_WIDTH_COLLAPSED = "64px";

export const Route = createFileRoute("/_authed")({
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
	const drawerOpen = useSidebarDrawerOpen();
	const sheetOpen = useRightPanelSheetOpen();
	const pickerOpen = useDocPickerOpen();
	const navigate = useNavigate();
	const search = useSearch({ strict: false });
	const activeChatId =
		typeof search.chatId === "string" && search.chatId.length > 0
			? search.chatId
			: null;
	const deleteConversation = useDeleteConversation();
	const { userId, email, status, signOut } = useAuth();
	const isBelowLg = useIsBelowLg();
	const sidebarShellRef = useRef<HTMLElement>(null);
	const rightPanelShellRef = useRef<HTMLElement>(null);

	useEffect(() => {
		if (status === "unauthed") {
			void navigate({ to: "/sign-in", replace: true });
		}
	}, [status, navigate]);

	useEffect(() => {
		if (!isBelowLg) {
			closeSidebarDrawer();
			closeRightPanelSheet();
		}
	}, [isBelowLg]);

	const sidebarIsModal = isBelowLg && drawerOpen;
	const rightPanelIsModal = isBelowLg && sheetOpen;
	const sidebarDialogProps: Record<string, unknown> = sidebarIsModal
		? {
				role: "dialog",
				"aria-modal": true,
				"aria-label": "Sidebar drawer",
				tabIndex: -1,
			}
		: {};

	useModalDialog({
		open: sidebarIsModal,
		containerRef: sidebarShellRef,
		onClose: closeSidebarDrawer,
	});
	useModalDialog({
		open: rightPanelIsModal,
		containerRef: rightPanelShellRef,
		onClose: closeRightPanelSheet,
	});

	const closeOverlays = useCallback(() => {
		closeDocPicker();
		closeRightPanelSheet();
		closeSidebarDrawer();
	}, []);

	const handleNewConversation = useCallback(() => {
		resetConversation({ navigate, closeOverlays }, { documentId: null });
	}, [navigate, closeOverlays]);

	const handleSignOut = useCallback(() => {
		signOut();
	}, [signOut]);

	const handlePickDocumentSelect = useCallback(
		(id: string) => {
			resetConversation({ navigate, closeOverlays }, { documentId: id });
		},
		[navigate, closeOverlays],
	);

	const handleSelectChat = useCallback(
		(chatId: string, documentId: string) => {
			closeSidebarDrawer();
			void navigate({
				to: "/app",
				search: (prev) => ({ ...prev, chatId, documentId }),
			});
		},
		[navigate],
	);

	const handleDeleteChat = useCallback(
		(chatId: string) => {
			deleteConversation.mutate(chatId, {
				onSuccess: () => {
					if (chatId === activeChatId) {
						resetConversation(
							{ navigate, closeOverlays },
							{ documentId: null },
						);
					}
				},
			});
		},
		[deleteConversation, activeChatId, navigate, closeOverlays],
	);

	const handlePickDocument = useCallback(() => {
		closeSidebarDrawer();
		openDocPicker();
	}, []);

	const handleChangeDocument = useCallback(() => {
		closeRightPanelSheet();
		openDocPicker();
	}, []);

	if (status === "loading") {
		return <AuthLoadingShell />;
	}

	if (status !== "authed") {
		return null;
	}

	const sidebarWidth = collapsed
		? SIDEBAR_WIDTH_COLLAPSED
		: SIDEBAR_WIDTH_EXPANDED;

	return (
		<div
			data-testid="authed-shell"
			data-right-panel={isRightPanelOpen ? "open" : "closed"}
			data-sidebar={collapsed ? "collapsed" : "expanded"}
			data-drawer={drawerOpen ? "open" : "closed"}
			data-sheet={sheetOpen ? "open" : "closed"}
			className="authed-grid h-screen w-screen overflow-hidden bg-background text-foreground"
			style={{ "--sb-w": sidebarWidth } as React.CSSProperties}
		>
			<button
				type="button"
				onClick={openSidebarDrawer}
				aria-label="Open sidebar"
				data-testid="sidebar-hamburger"
				className="fixed top-3 left-3 z-30 inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card text-foreground shadow-sm hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring lg:hidden"
			>
				<Menu aria-hidden="true" className="size-4" />
			</button>
			<aside
				ref={sidebarShellRef}
				data-testid="sidebar-shell"
				{...sidebarDialogProps}
				className={cn(
					"fixed inset-y-0 left-0 z-50 h-full transition-transform duration-200 ease-out",
					"lg:relative lg:inset-y-auto lg:left-auto lg:z-auto lg:translate-x-0 lg:transition-none",
					drawerOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
				)}
				style={{ width: sidebarWidth }}
			>
				<Sidebar
					collapsed={collapsed}
					userId={userId ?? ""}
					email={email}
					onToggleCollapse={toggleSidebar}
					onNewConversation={handleNewConversation}
					onPickDocument={handlePickDocument}
					onSelectChat={handleSelectChat}
					onDeleteChat={handleDeleteChat}
					onSignOut={handleSignOut}
				/>
			</aside>
			{drawerOpen ? (
				<button
					type="button"
					aria-label="Close sidebar"
					data-testid="sidebar-backdrop"
					onClick={closeSidebarDrawer}
					className="fixed inset-0 z-40 bg-foreground/40 backdrop-blur-sm lg:hidden"
				/>
			) : null}
			<div className="flex h-full min-w-0 flex-col overflow-hidden">
				<Outlet />
			</div>
			{pinnedDocumentId !== null ? (
				<RightPanel
					ref={rightPanelShellRef}
					documentId={pinnedDocumentId}
					onChangeDocument={handleChangeDocument}
					onClose={closeRightPanelSheet}
					modal={rightPanelIsModal}
					className={cn(
						"fixed inset-x-0 bottom-0 z-50 h-[90vh] border-border border-t shadow-lg transition-transform duration-200 ease-out",
						"lg:relative lg:inset-auto lg:bottom-auto lg:z-auto lg:h-full lg:border-t-0 lg:border-l lg:shadow-none lg:translate-y-0 lg:transition-none",
						sheetOpen ? "translate-y-0" : "translate-y-full lg:translate-y-0",
					)}
				/>
			) : null}
			{sheetOpen && pinnedDocumentId !== null ? (
				<button
					type="button"
					aria-label="Close document panel"
					data-testid="right-panel-backdrop"
					onClick={closeRightPanelSheet}
					className="fixed inset-0 z-40 bg-foreground/40 backdrop-blur-sm lg:hidden"
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

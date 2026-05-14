import { useStore } from "@tanstack/react-store";
import { Store } from "@tanstack/store";

export type ResponsiveState = {
	drawerOpen: boolean;
	rightPanelSheetOpen: boolean;
};

const DEFAULT_STATE: ResponsiveState = {
	drawerOpen: false,
	rightPanelSheetOpen: false,
};

export function createResponsiveStore(): Store<ResponsiveState> {
	return new Store<ResponsiveState>(DEFAULT_STATE);
}

export const responsiveStore = createResponsiveStore();

export function openSidebarDrawer(): void {
	responsiveStore.setState((state) => ({ ...state, drawerOpen: true }));
}

export function closeSidebarDrawer(): void {
	if (!responsiveStore.state.drawerOpen) return;
	responsiveStore.setState((state) => ({ ...state, drawerOpen: false }));
}

export function toggleSidebarDrawer(): void {
	responsiveStore.setState((state) => ({
		...state,
		drawerOpen: !state.drawerOpen,
	}));
}

export function useSidebarDrawerOpen(): boolean {
	return useStore(responsiveStore, (state) => state.drawerOpen);
}

export function openRightPanelSheet(): void {
	if (responsiveStore.state.rightPanelSheetOpen) return;
	responsiveStore.setState((state) => ({
		...state,
		rightPanelSheetOpen: true,
	}));
}

export function closeRightPanelSheet(): void {
	if (!responsiveStore.state.rightPanelSheetOpen) return;
	responsiveStore.setState((state) => ({
		...state,
		rightPanelSheetOpen: false,
	}));
}

export function useRightPanelSheetOpen(): boolean {
	return useStore(responsiveStore, (state) => state.rightPanelSheetOpen);
}

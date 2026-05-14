import { useStore } from "@tanstack/react-store";
import { Store } from "@tanstack/store";

export type ResponsiveState = {
	drawerOpen: boolean;
};

const DEFAULT_STATE: ResponsiveState = { drawerOpen: false };

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

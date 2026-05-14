import { useStore } from "@tanstack/react-store";
import { Store } from "@tanstack/store";

export const SIDEBAR_STORAGE_KEY = "convfinqa:sidebar";

export type SidebarState = {
	collapsed: boolean;
};

const DEFAULT_STATE: SidebarState = { collapsed: false };

function readPersistedState(): SidebarState {
	try {
		const raw = window.localStorage.getItem(SIDEBAR_STORAGE_KEY);
		if (raw === null) return DEFAULT_STATE;
		const parsed: unknown = JSON.parse(raw);
		if (
			typeof parsed === "object" &&
			parsed !== null &&
			"collapsed" in parsed &&
			typeof (parsed as { collapsed: unknown }).collapsed === "boolean"
		) {
			return { collapsed: (parsed as { collapsed: boolean }).collapsed };
		}
	} catch {
		// Corrupt JSON or storage blocked — fall through to defaults.
	}
	return DEFAULT_STATE;
}

function writePersistedState(state: SidebarState): void {
	try {
		window.localStorage.setItem(SIDEBAR_STORAGE_KEY, JSON.stringify(state));
	} catch {
		// Quota exceeded or storage blocked — silently drop the write.
	}
}

export function createSidebarStore(): Store<SidebarState> {
	const store = new Store<SidebarState>(readPersistedState());
	store.subscribe(() => writePersistedState(store.state));
	return store;
}

export const sidebarStore = createSidebarStore();

export function toggleSidebar(): void {
	sidebarStore.setState((state) => ({ ...state, collapsed: !state.collapsed }));
}

export function setSidebarCollapsed(collapsed: boolean): void {
	sidebarStore.setState((state) => ({ ...state, collapsed }));
}

export function useSidebarCollapsed(): boolean {
	return useStore(sidebarStore, (state) => state.collapsed);
}

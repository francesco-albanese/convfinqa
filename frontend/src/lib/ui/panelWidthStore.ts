import { useStore } from "@tanstack/react-store";
import { Store } from "@tanstack/store";

export const PANEL_WIDTH_STORAGE_KEY = "convfinqa:panelWidth";
export const PANEL_WIDTH_DEFAULT = 480;
export const PANEL_WIDTH_MIN = 240;
export const PANEL_WIDTH_MAX_FRACTION = 0.6;

export type PanelWidthState = {
	width: number;
};

const DEFAULT_STATE: PanelWidthState = { width: PANEL_WIDTH_DEFAULT };

function clampToMin(width: number): number {
	return width < PANEL_WIDTH_MIN ? PANEL_WIDTH_MIN : width;
}

export function clampPanelWidth(width: number, viewportWidth: number): number {
	const max = Math.max(
		PANEL_WIDTH_MIN,
		viewportWidth * PANEL_WIDTH_MAX_FRACTION,
	);
	if (!Number.isFinite(width)) return PANEL_WIDTH_DEFAULT;
	if (width < PANEL_WIDTH_MIN) return PANEL_WIDTH_MIN;
	if (width > max) return max;
	return width;
}

function readPersistedState(): PanelWidthState {
	try {
		const raw = window.localStorage.getItem(PANEL_WIDTH_STORAGE_KEY);
		if (raw === null) return DEFAULT_STATE;
		const parsed: unknown = JSON.parse(raw);
		if (
			typeof parsed === "object" &&
			parsed !== null &&
			"width" in parsed &&
			typeof (parsed as { width: unknown }).width === "number" &&
			Number.isFinite((parsed as { width: number }).width)
		) {
			return { width: clampToMin((parsed as { width: number }).width) };
		}
	} catch {
		// Corrupt JSON or storage blocked — fall through to defaults.
	}
	return DEFAULT_STATE;
}

function writePersistedState(state: PanelWidthState): void {
	try {
		window.localStorage.setItem(PANEL_WIDTH_STORAGE_KEY, JSON.stringify(state));
	} catch {
		// Quota exceeded or storage blocked — silently drop the write.
	}
}

export function createPanelWidthStore(): Store<PanelWidthState> {
	const store = new Store<PanelWidthState>(readPersistedState());
	store.subscribe(() => writePersistedState(store.state));
	return store;
}

export const panelWidthStore = createPanelWidthStore();

export function setPanelWidth(width: number): void {
	panelWidthStore.setState((state) => ({ ...state, width: clampToMin(width) }));
}

export function resetPanelWidth(): void {
	panelWidthStore.setState((state) => ({
		...state,
		width: PANEL_WIDTH_DEFAULT,
	}));
}

export function usePanelWidth(): number {
	return useStore(panelWidthStore, (state) => state.width);
}

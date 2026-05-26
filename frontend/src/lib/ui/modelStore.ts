import { useStore } from "@tanstack/react-store";
import { Store } from "@tanstack/store";

export const MODEL_STORAGE_KEY = "convfinqa:model";

export type ModelState = {
	selected: string | null;
};

const DEFAULT_STATE: ModelState = { selected: null };

function readPersistedState(): ModelState {
	try {
		const raw = window.localStorage.getItem(MODEL_STORAGE_KEY);
		if (raw === null) return DEFAULT_STATE;
		const parsed: unknown = JSON.parse(raw);
		if (
			typeof parsed === "object" &&
			parsed !== null &&
			"selected" in parsed &&
			typeof (parsed as { selected: unknown }).selected === "string"
		) {
			return { selected: (parsed as { selected: string }).selected };
		}
	} catch {
		// Corrupt JSON or storage blocked — fall through to defaults.
	}
	return DEFAULT_STATE;
}

function writePersistedState(state: ModelState): void {
	try {
		window.localStorage.setItem(MODEL_STORAGE_KEY, JSON.stringify(state));
	} catch {
		// Quota exceeded or storage blocked — silently drop the write.
	}
}

export function createModelStore(): Store<ModelState> {
	const store = new Store<ModelState>(readPersistedState());
	store.subscribe(() => writePersistedState(store.state));
	return store;
}

export const modelStore = createModelStore();

export function setSelectedModel(model: string): void {
	modelStore.setState((state) => ({ ...state, selected: model }));
}

export function useSelectedModel(): string | null {
	return useStore(modelStore, (state) => state.selected);
}

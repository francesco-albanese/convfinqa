import { useStore } from "@tanstack/react-store";
import { Store } from "@tanstack/store";

export type DocPickerState = {
	open: boolean;
};

const DEFAULT_STATE: DocPickerState = { open: false };

export function createDocPickerStore(): Store<DocPickerState> {
	return new Store<DocPickerState>(DEFAULT_STATE);
}

export const docPickerStore = createDocPickerStore();

export function openDocPicker(): void {
	docPickerStore.setState((state) => ({ ...state, open: true }));
}

export function closeDocPicker(): void {
	docPickerStore.setState((state) => ({ ...state, open: false }));
}

export function setDocPickerOpen(open: boolean): void {
	docPickerStore.setState((state) => ({ ...state, open }));
}

export function useDocPickerOpen(): boolean {
	return useStore(docPickerStore, (state) => state.open);
}

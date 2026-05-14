import { useStore } from "@tanstack/react-store";
import { Store } from "@tanstack/store";
import {
	type EffectiveTheme,
	isThemeMode,
	resolveInitialTheme,
	type ThemeMode,
} from "@/theme/resolveInitialTheme";

// Coupled with the inline bootstrap script in `index.html` (see convfinqa-uf5.2):
// both must reference the same literal string since the bootstrap runs before
// any bundle loads and cannot import this constant.
export const THEME_STORAGE_KEY = "convfinqa:theme.mode";

export type { EffectiveTheme, ThemeMode } from "@/theme/resolveInitialTheme";

export type ThemeState = {
	mode: ThemeMode;
	effectiveTheme: EffectiveTheme;
};

const LIGHT_MEDIA_QUERY = "(prefers-color-scheme: light)";

function readPersistedMode(): string | null {
	try {
		return window.localStorage.getItem(THEME_STORAGE_KEY);
	} catch {
		return null;
	}
}

function writePersistedMode(mode: ThemeMode): void {
	try {
		window.localStorage.setItem(THEME_STORAGE_KEY, mode);
	} catch {
		// Quota exceeded or storage blocked — silently drop the write.
	}
}

function systemPrefersLight(): boolean {
	if (
		typeof window === "undefined" ||
		typeof window.matchMedia !== "function"
	) {
		return false;
	}
	return window.matchMedia(LIGHT_MEDIA_QUERY).matches;
}

function resolveEffectiveTheme(mode: ThemeMode): EffectiveTheme {
	return resolveInitialTheme(mode, systemPrefersLight());
}

export function createThemeStore(): Store<ThemeState> {
	const raw = readPersistedMode();
	const initialMode: ThemeMode = isThemeMode(raw) ? raw : "system";
	const store = new Store<ThemeState>({
		mode: initialMode,
		effectiveTheme: resolveInitialTheme(raw, systemPrefersLight()),
	});

	store.subscribe(() => writePersistedMode(store.state.mode));

	if (
		typeof window !== "undefined" &&
		typeof window.matchMedia === "function"
	) {
		const mql = window.matchMedia(LIGHT_MEDIA_QUERY);
		mql.addEventListener("change", (event) => {
			if (store.state.mode !== "system") return;
			store.setState((state) => ({
				...state,
				effectiveTheme: event.matches ? "light" : "dark",
			}));
		});
	}

	return store;
}

export function applyMode(store: Store<ThemeState>, mode: ThemeMode): void {
	store.setState(() => ({
		mode,
		effectiveTheme: resolveEffectiveTheme(mode),
	}));
}

export const themeStore = createThemeStore();

export function setMode(mode: ThemeMode): void {
	applyMode(themeStore, mode);
}

export function useThemeMode(): ThemeMode {
	return useStore(themeStore, (state) => state.mode);
}

export function useEffectiveTheme(): EffectiveTheme {
	return useStore(themeStore, (state) => state.effectiveTheme);
}

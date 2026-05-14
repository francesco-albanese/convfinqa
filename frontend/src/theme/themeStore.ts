import { useStore } from "@tanstack/react-store";
import { Store } from "@tanstack/store";

// Coupled with the inline bootstrap script in `index.html` (see convfinqa-uf5.2):
// both must reference the same literal string since the bootstrap runs before
// any bundle loads and cannot import this constant.
export const THEME_STORAGE_KEY = "convfinqa:theme.mode";

export type ThemeMode = "system" | "light" | "dark";
export type EffectiveTheme = "light" | "dark";

export type ThemeState = {
	mode: ThemeMode;
	effectiveTheme: EffectiveTheme;
};

const LIGHT_MEDIA_QUERY = "(prefers-color-scheme: light)";
const DEFAULT_MODE: ThemeMode = "system";

function isThemeMode(value: unknown): value is ThemeMode {
	return value === "system" || value === "light" || value === "dark";
}

function readPersistedMode(): ThemeMode {
	try {
		const raw = window.localStorage.getItem(THEME_STORAGE_KEY);
		if (isThemeMode(raw)) return raw;
	} catch {
		// Storage blocked — fall through to default.
	}
	return DEFAULT_MODE;
}

function writePersistedMode(mode: ThemeMode): void {
	try {
		window.localStorage.setItem(THEME_STORAGE_KEY, mode);
	} catch {
		// Quota exceeded or storage blocked — silently drop the write.
	}
}

function getSystemEffectiveTheme(): EffectiveTheme {
	if (
		typeof window === "undefined" ||
		typeof window.matchMedia !== "function"
	) {
		return "dark";
	}
	return window.matchMedia(LIGHT_MEDIA_QUERY).matches ? "light" : "dark";
}

function resolveEffectiveTheme(mode: ThemeMode): EffectiveTheme {
	return mode === "system" ? getSystemEffectiveTheme() : mode;
}

export function createThemeStore(): Store<ThemeState> {
	const initialMode = readPersistedMode();
	const store = new Store<ThemeState>({
		mode: initialMode,
		effectiveTheme: resolveEffectiveTheme(initialMode),
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

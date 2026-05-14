export type ThemeMode = "system" | "light" | "dark";
export type EffectiveTheme = "light" | "dark";

export function isThemeMode(value: unknown): value is ThemeMode {
	return value === "system" || value === "light" || value === "dark";
}

// Mirrored verbatim by the inline bootstrap <script> in `frontend/index.html`.
// The inline script must paint `<html data-theme>` before any bundle loads, so
// it cannot import this module. When changing this logic, update the script in
// index.html too — the resolveInitialTheme unit tests enforce parity at the
// input/output level (matrix of storage value × system preference).
export function resolveInitialTheme(
	storageValue: string | null,
	systemPrefersLight: boolean,
): EffectiveTheme {
	const mode: ThemeMode = isThemeMode(storageValue) ? storageValue : "system";
	if (mode === "system") return systemPrefersLight ? "light" : "dark";
	return mode;
}

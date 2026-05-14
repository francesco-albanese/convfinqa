import { useEffect } from "react";
import { useEffectiveTheme } from "@/theme/themeStore";

// The inline <script> in index.html paints `<html data-theme>` before any
// bundle loads (no-flash). This hook keeps the attribute in sync with the
// store afterwards, e.g. when the user toggles via the UserMenu or the OS
// flips its prefers-color-scheme while in `mode: 'system'`.
export function useApplyEffectiveTheme(): void {
	const effectiveTheme = useEffectiveTheme();

	useEffect(() => {
		document.documentElement.dataset.theme = effectiveTheme;
	}, [effectiveTheme]);
}

import { useEffect, useState } from "react";

const LG_QUERY = "(min-width: 1024px)";

export function useIsBelowLg(): boolean {
	const [isBelowLg, setIsBelowLg] = useState(() => {
		if (typeof window === "undefined" || !window.matchMedia) return false;
		return !window.matchMedia(LG_QUERY).matches;
	});

	useEffect(() => {
		if (typeof window === "undefined" || !window.matchMedia) return;
		const mq = window.matchMedia(LG_QUERY);
		setIsBelowLg(!mq.matches);
		const handle = (event: MediaQueryListEvent) => {
			setIsBelowLg(!event.matches);
		};
		mq.addEventListener("change", handle);
		return () => mq.removeEventListener("change", handle);
	}, []);

	return isBelowLg;
}

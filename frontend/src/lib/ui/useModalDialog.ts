import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR =
	'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, [tabindex]:not([tabindex="-1"]), [contenteditable="true"]';

function getFocusables(container: HTMLElement): HTMLElement[] {
	return Array.from(
		container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
	);
}

function pickInitialFocus(container: HTMLElement): HTMLElement {
	const explicit = container.querySelector<HTMLElement>(
		"[data-modal-initial-focus]",
	);
	if (explicit !== null) return explicit;
	const first = getFocusables(container)[0];
	return first ?? container;
}

export type UseModalDialogOptions = {
	open: boolean;
	containerRef: React.RefObject<HTMLElement | null>;
	onClose: () => void;
};

export function useModalDialog({
	open,
	containerRef,
	onClose,
}: UseModalDialogOptions): void {
	const triggerRef = useRef<HTMLElement | null>(null);

	useEffect(() => {
		if (!open) return;
		const container = containerRef.current;
		if (container === null) return;

		triggerRef.current =
			document.activeElement instanceof HTMLElement
				? document.activeElement
				: null;

		pickInitialFocus(container).focus({ preventScroll: true });

		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				event.preventDefault();
				onClose();
				return;
			}
			if (event.key !== "Tab") return;
			const focusables = getFocusables(container);
			if (focusables.length === 0) {
				event.preventDefault();
				container.focus();
				return;
			}
			const first = focusables[0];
			const last = focusables[focusables.length - 1];
			if (first === undefined || last === undefined) return;
			const active = document.activeElement;
			const inside = active instanceof Node && container.contains(active);
			if (event.shiftKey) {
				if (!inside || active === first) {
					event.preventDefault();
					last.focus();
				}
				return;
			}
			if (!inside || active === last) {
				event.preventDefault();
				first.focus();
			}
		};

		container.addEventListener("keydown", onKeyDown);
		return () => {
			container.removeEventListener("keydown", onKeyDown);
			const previous = triggerRef.current;
			triggerRef.current = null;
			if (previous !== null && document.body.contains(previous)) {
				previous.focus({ preventScroll: true });
			}
		};
	}, [open, containerRef, onClose]);
}

import type { UIMessage } from "ai";

export type ChatResetControls = {
	stop: () => void;
	setMessages: (messages: UIMessage[]) => void;
};

let registered: ChatResetControls | null = null;

export function registerChatResetControls(controls: ChatResetControls): void {
	registered = controls;
}

export function clearChatResetControls(controls: ChatResetControls): void {
	if (registered === controls) {
		registered = null;
	}
}

export type ResetConversationDeps = {
	navigate: (opts: {
		to: "/app";
		search: () => Record<string, unknown>;
	}) => void;
	closeOverlays: () => void;
	getControls?: () => ChatResetControls | null;
};

export function resetConversation(
	deps: ResetConversationDeps,
	options: { documentId: string | null },
): void {
	const controls = deps.getControls ? deps.getControls() : registered;
	controls?.stop();
	controls?.setMessages([]);
	deps.closeOverlays();
	deps.navigate({
		to: "/app",
		search: () =>
			options.documentId ? { documentId: options.documentId } : {},
	});
}

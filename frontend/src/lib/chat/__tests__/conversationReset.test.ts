import type { UIMessage } from "ai";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
	type ChatResetControls,
	clearChatResetControls,
	registerChatResetControls,
	resetConversation,
} from "@/lib/chat/conversationReset";

type NavigateArg = { to: "/app"; search: () => Record<string, unknown> };

function makeControls(): ChatResetControls & {
	stop: ReturnType<typeof vi.fn>;
	setMessages: ReturnType<typeof vi.fn>;
} {
	return {
		stop: vi.fn<() => void>(),
		setMessages: vi.fn<(messages: UIMessage[]) => void>(),
	};
}

afterEach(() => {
	const orphan = makeControls();
	registerChatResetControls(orphan);
	clearChatResetControls(orphan);
});

describe("resetConversation", () => {
	it("stops the stream, empties messages, closes overlays, and lands on empty /app when documentId is null", () => {
		const controls = makeControls();
		const closeOverlays = vi.fn();
		const navigate = vi.fn<(arg: NavigateArg) => void>();

		resetConversation(
			{ navigate, closeOverlays, getControls: () => controls },
			{ documentId: null },
		);

		expect(controls.stop).toHaveBeenCalledOnce();
		expect(controls.setMessages).toHaveBeenCalledWith([]);
		expect(closeOverlays).toHaveBeenCalledOnce();
		const arg = navigate.mock.calls[0]?.[0];
		expect(arg?.to).toBe("/app");
		expect(arg?.search()).toEqual({});
	});

	it("keeps the documentId in the search when reset pins a new document", () => {
		const controls = makeControls();
		const navigate = vi.fn<(arg: NavigateArg) => void>();

		resetConversation(
			{ navigate, closeOverlays: vi.fn(), getControls: () => controls },
			{ documentId: "doc-42" },
		);

		expect(navigate.mock.calls[0]?.[0]?.search()).toEqual({
			documentId: "doc-42",
		});
	});

	it("is a harmless no-op for controls when none are registered", () => {
		const navigate = vi.fn<(arg: NavigateArg) => void>();
		const closeOverlays = vi.fn();

		resetConversation(
			{ navigate, closeOverlays, getControls: () => null },
			{ documentId: null },
		);

		expect(closeOverlays).toHaveBeenCalledOnce();
		expect(navigate).toHaveBeenCalledOnce();
	});
});

describe("chat reset registry", () => {
	it("routes the default getControls path to the registered controls", () => {
		const controls = makeControls();
		registerChatResetControls(controls);

		resetConversation(
			{ navigate: vi.fn(), closeOverlays: vi.fn() },
			{ documentId: null },
		);

		expect(controls.stop).toHaveBeenCalledOnce();
		expect(controls.setMessages).toHaveBeenCalledWith([]);

		clearChatResetControls(controls);
	});

	it("does not touch cleared controls and only clears on identity match", () => {
		const first = makeControls();
		const second = makeControls();
		registerChatResetControls(first);
		registerChatResetControls(second);

		clearChatResetControls(first);

		resetConversation(
			{ navigate: vi.fn(), closeOverlays: vi.fn() },
			{ documentId: null },
		);

		expect(first.stop).not.toHaveBeenCalled();
		expect(second.stop).toHaveBeenCalledOnce();

		clearChatResetControls(second);

		resetConversation(
			{ navigate: vi.fn(), closeOverlays: vi.fn() },
			{ documentId: null },
		);

		expect(second.stop).toHaveBeenCalledOnce();
	});
});

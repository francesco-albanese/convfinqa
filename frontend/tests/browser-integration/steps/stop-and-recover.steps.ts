import { expect, type Page } from "@playwright/test";
import { createBdd } from "playwright-bdd";

const { Given, When, Then, Before } = createBdd();

type StreamDescriptor = {
	kind: "stream";
	partial: string;
	rest: string;
	conversationId: string;
	hold: boolean;
};

type ConflictDescriptor = {
	kind: "conflict";
};

type ChatMockNext = StreamDescriptor | ConflictDescriptor;

type ChatMockState = {
	queue: ChatMockNext[];
	installed: boolean;
};

declare global {
	// eslint-disable-next-line no-var
	var __chatMockState: ChatMockState | undefined;
}

async function installChatMockBackend(page: Page): Promise<void> {
	await page.addInitScript(() => {
		const existing = globalThis.__chatMockState;
		if (existing?.installed) {
			existing.queue = [];
			return;
		}
		const state: ChatMockState = { queue: [], installed: true };
		globalThis.__chatMockState = state;

		const sseFrame = (frame: object): string =>
			`data: ${JSON.stringify(frame)}\n\n`;
		const encoder = new TextEncoder();

		const buildStreamResponse = (
			descriptor: StreamDescriptor,
			signal: AbortSignal | undefined,
		): Response => {
			const stream = new ReadableStream<Uint8Array>({
				start(controller) {
					const close = () => {
						try {
							controller.close();
						} catch {
							// already closed
						}
					};

					controller.enqueue(
						encoder.encode(sseFrame({ type: "start", messageId: "msg-mock" })),
					);
					controller.enqueue(
						encoder.encode(
							sseFrame({
								type: "data-conversation",
								data: { conversationId: descriptor.conversationId },
							}),
						),
					);
					controller.enqueue(
						encoder.encode(sseFrame({ type: "text-start", id: "msg-mock" })),
					);
					if (descriptor.partial.length > 0) {
						controller.enqueue(
							encoder.encode(
								sseFrame({
									type: "text-delta",
									id: "msg-mock",
									delta: descriptor.partial,
								}),
							),
						);
					}

					if (descriptor.hold) {
						signal?.addEventListener("abort", close, { once: true });
						return;
					}

					if (descriptor.rest.length > 0) {
						controller.enqueue(
							encoder.encode(
								sseFrame({
									type: "text-delta",
									id: "msg-mock",
									delta: descriptor.rest,
								}),
							),
						);
					}
					controller.enqueue(
						encoder.encode(sseFrame({ type: "text-end", id: "msg-mock" })),
					);
					controller.enqueue(encoder.encode(sseFrame({ type: "finish" })));
					controller.enqueue(encoder.encode("data: [DONE]\n\n"));
					close();
				},
			});

			return new Response(stream, {
				status: 200,
				headers: {
					"content-type": "text/event-stream",
					"cache-control": "no-cache",
					"x-vercel-ai-ui-message-stream": "v1",
				},
			});
		};

		const conflictResponse = (): Response =>
			new Response(
				JSON.stringify({
					type: "about:blank/conversation-busy",
					title: "Conversation busy",
					status: 409,
					detail: "Another response is in progress.",
				}),
				{
					status: 409,
					headers: { "content-type": "application/problem+json" },
				},
			);

		const originalFetch = globalThis.fetch.bind(globalThis);
		globalThis.fetch = async (input, init) => {
			const url =
				typeof input === "string"
					? input
					: input instanceof URL
						? input.toString()
						: input.url;

			if (url.endsWith("/v1/chats")) {
				// Sidebar query fires on /app load; without a stub it would proxy
				// to an absent backend. Safe to short-circuit globally only because
				// the Before hook is tag-scoped to @stop-recover.
				return new Response(JSON.stringify({ items: [] }), {
					status: 200,
					headers: { "content-type": "application/json" },
				});
			}

			if (url.includes("/v1/chat/stream")) {
				const next = state.queue.shift();
				if (!next) {
					return new Response("no mock queued", { status: 500 });
				}
				if (next.kind === "conflict") {
					return conflictResponse();
				}
				return buildStreamResponse(next, init?.signal ?? undefined);
			}

			return originalFetch(input, init);
		};
	});
}

Before({ tags: "@stop-recover" }, async ({ page }) => {
	await installChatMockBackend(page);
});

async function pushMock(page: Page, next: ChatMockNext): Promise<void> {
	await page.evaluate((descriptor) => {
		globalThis.__chatMockState?.queue.push(descriptor);
	}, next);
}

Given(
	"the next chat stream emits {string} then holds",
	async ({ page }, partial: string) => {
		await pushMock(page, {
			kind: "stream",
			partial,
			rest: "",
			conversationId: "conv-stop",
			hold: true,
		});
	},
);

Given("the next chat stream responds with a 409 conflict", async ({ page }) => {
	await pushMock(page, { kind: "conflict" });
});

Given(
	"the chat stream after that emits {string} in one chunk",
	async ({ page }, text: string) => {
		await pushMock(page, {
			kind: "stream",
			partial: "",
			rest: text,
			conversationId: "conv-recover",
			hold: false,
		});
	},
);

When("I click the stop button", async ({ page }) => {
	await page.getByRole("button", { name: "Stop generating" }).click();
});

When("I click the retry button on the banner", async ({ page }) => {
	await page
		.getByTestId("stream-error-banner")
		.getByRole("button", { name: /^Retry/ })
		.click();
});

Then(
	"the assistant message shows a {string} badge",
	async ({ page }, label: string) => {
		const badge = page.getByTestId("stopped-badge");
		await expect(badge).toBeVisible();
		await expect(badge).toHaveText(label);
	},
);

Then(
	"I see the stream error banner with title {string}",
	async ({ page }, title: string) => {
		const banner = page.getByTestId("stream-error-banner");
		await expect(banner).toBeVisible();
		await expect(banner).toContainText(title);
	},
);

Then("I see the retry button on the banner", async ({ page }) => {
	await expect(
		page
			.getByTestId("stream-error-banner")
			.getByRole("button", { name: /^Retry/ }),
	).toBeVisible();
});

Then("the stream error banner is gone", async ({ page }) => {
	await expect(page.getByTestId("stream-error-banner")).toHaveCount(0);
});

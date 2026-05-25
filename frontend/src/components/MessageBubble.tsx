import type { DynamicToolUIPart, TextUIPart, UIMessage } from "ai";
import { isReasoningUIPart } from "ai";
import { Streamdown } from "streamdown";
import { ThinkingDisclosure } from "@/components/ThinkingDisclosure";
import type { CitationData } from "@/lib/chat/schemas";
import { safeUrlTransform } from "@/lib/markdown/safeUrl";
import { cn } from "@/lib/utils";

const DISALLOWED_ELEMENTS = [
	"img",
	"iframe",
	"object",
	"embed",
	"form",
	"input",
	"button",
	"script",
	"style",
] as const;

type MessageBubbleProps = {
	message: UIMessage;
	showCursor?: boolean;
	stopped?: boolean;
	citations?: ReadonlyArray<CitationData>;
};

export function MessageBubble({
	message,
	showCursor,
	stopped,
	citations,
}: MessageBubbleProps) {
	const text = extractText(message);
	const isUser = message.role === "user";

	if (isUser) {
		return (
			<div className="flex justify-end">
				<div
					data-role="user"
					className="max-w-[80%] whitespace-pre-wrap break-words rounded-2xl bg-secondary px-4 py-2 text-sm leading-6 text-secondary-foreground"
				>
					{text}
				</div>
			</div>
		);
	}

	let toolStepIndex = 0;

	return (
		<div className="flex justify-start">
			<div
				data-role="assistant"
				className={cn(
					"max-w-[80%] break-words text-sm leading-6 text-foreground",
					"prose-headings:font-semibold",
				)}
			>
				{message.parts.map((part, idx) => {
					if (isReasoningUIPart(part)) {
						return (
							<ThinkingDisclosure
								// biome-ignore lint/suspicious/noArrayIndexKey: ReasoningUIPart has no stable id; parts order is immutable after stream ends
								key={`${message.id}-r-${idx}`}
								text={part.text}
								isStreaming={part.state === "streaming"}
							/>
						);
					}
					if (part.type === "dynamic-tool") {
						const stepNum = ++toolStepIndex;
						return (
							<ToolStepRow
								// biome-ignore lint/suspicious/noArrayIndexKey: tool parts are ordered; toolCallId may duplicate across replays
								key={`${message.id}-t-${idx}`}
								part={part}
								stepNumber={stepNum}
							/>
						);
					}
					return null;
				})}
				<Streamdown
					controls={false}
					disallowedElements={DISALLOWED_ELEMENTS}
					urlTransform={safeUrlTransform}
					components={{
						p: ({ children }) => (
							<p className="my-2 first:mt-0 last:mb-0">{children}</p>
						),
						ul: ({ children }) => (
							<ul className="my-2 list-disc pl-5">{children}</ul>
						),
						ol: ({ children }) => (
							<ol className="my-2 list-decimal pl-5">{children}</ol>
						),
						li: ({ children }) => <li className="my-1">{children}</li>,
						strong: ({ children }) => (
							<strong className="font-semibold">{children}</strong>
						),
						em: ({ children }) => <em className="italic">{children}</em>,
						code: ({ children }) => (
							<code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
								{children}
							</code>
						),
						pre: ({ children }) => (
							<pre className="my-2 overflow-x-auto rounded bg-muted p-3 font-mono text-xs">
								{children}
							</pre>
						),
						a: ({ href, children }) => (
							<a
								href={href}
								target="_blank"
								rel="noopener noreferrer"
								className="text-link underline-offset-2 hover:underline"
							>
								{children}
							</a>
						),
					}}
				>
					{text}
				</Streamdown>
				{showCursor && (
					<span
						data-testid="streaming-cursor"
						aria-hidden="true"
						className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse bg-primary align-baseline"
					/>
				)}
				{stopped && (
					<div className="mt-2">
						<span
							data-testid="stopped-badge"
							className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 font-medium text-muted-foreground text-xs"
						>
							Stopped
						</span>
					</div>
				)}
				{citations && citations.length > 0 && (
					<div
						data-testid="citation-chips"
						className="mt-3 flex flex-wrap gap-1.5"
					>
						{citations.map((c) => (
							<CitationChip
								key={`${c.rowLabel}·${c.colLabel}`}
								rowLabel={c.rowLabel}
								colLabel={c.colLabel}
							/>
						))}
					</div>
				)}
			</div>
		</div>
	);
}

type CitationChipProps = {
	rowLabel: string;
	colLabel: string;
};

function CitationChip({ rowLabel, colLabel }: CitationChipProps) {
	return (
		<span
			data-testid="citation-chip"
			className="inline-flex items-center gap-1 rounded-md border border-border bg-muted px-2 py-0.5 font-mono text-muted-foreground text-xs"
		>
			<span>{rowLabel}</span>
			<span className="opacity-40">·</span>
			<span>{colLabel}</span>
		</span>
	);
}

type ToolStepRowProps = {
	part: DynamicToolUIPart;
	stepNumber: number;
};

function formatArgs(toolName: string, input: unknown): string {
	if (input === null || input === undefined) return "";
	if (typeof input !== "object") return String(input);
	if (toolName === "sql_query") {
		const sqlInput = input as { sql?: unknown };
		return typeof sqlInput.sql === "string" ? sqlInput.sql : "";
	}
	const entries = Object.entries(input as Record<string, unknown>);
	if (entries.length === 0) return "";
	return entries.map(([k, v]) => `${k}="${String(v)}"`).join(", ");
}

function formatOutput(part: DynamicToolUIPart): string {
	if (part.state === "output-error") {
		return `ERROR: ${part.errorText}`;
	}
	if (part.state === "output-available") {
		if (part.output === null || part.output === undefined) return "";
		if (part.toolName === "sql_query" && typeof part.output === "object") {
			const out = part.output as { rows?: unknown[]; truncated?: boolean };
			const count = Array.isArray(out.rows) ? out.rows.length : 0;
			const suffix = out.truncated ? "+" : "";
			return `${count}${suffix} ${count === 1 ? "row" : "rows"}`;
		}
		if (typeof part.output === "object") {
			const entries = Object.entries(part.output as Record<string, unknown>);
			if (entries.length === 1) return String(entries[0]?.[1] ?? "");
			return JSON.stringify(part.output);
		}
		return String(part.output);
	}
	return "";
}

function ToolStepRow({ part, stepNumber }: ToolStepRowProps) {
	const num = String(stepNumber).padStart(2, "0");
	const args = formatArgs(part.toolName, part.input);
	const call = args ? `${part.toolName}(${args})` : `${part.toolName}()`;
	const isPendingResult =
		part.state === "input-streaming" || part.state === "input-available";
	const output = isPendingResult ? null : formatOutput(part);
	const isError = part.state === "output-error";

	return (
		<div
			data-testid="tool-step"
			className="my-1.5 flex items-baseline gap-2 font-mono text-xs text-muted-foreground"
		>
			<span className="shrink-0 tabular-nums opacity-50">{num}</span>
			<span className="min-w-0 break-all">
				<span>{call}</span>
				{output !== null && (
					<>
						<span className="mx-1 opacity-50">→</span>
						<span className={isError ? "text-destructive" : undefined}>
							{output}
						</span>
					</>
				)}
			</span>
		</div>
	);
}

function extractText(message: UIMessage): string {
	return message.parts
		.filter((part): part is TextUIPart => part.type === "text")
		.map((part) => part.text)
		.join("");
}

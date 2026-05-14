import type { TextUIPart, UIMessage } from "ai";
import { Streamdown } from "streamdown";
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
};

export function MessageBubble({
	message,
	showCursor,
	stopped,
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

	return (
		<div className="flex justify-start">
			<div
				data-role="assistant"
				className={cn(
					"max-w-[80%] break-words text-sm leading-6 text-foreground",
					"prose-headings:font-semibold",
				)}
			>
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
			</div>
		</div>
	);
}

function extractText(message: UIMessage): string {
	return message.parts
		.filter((part): part is TextUIPart => part.type === "text")
		.map((part) => part.text)
		.join("");
}

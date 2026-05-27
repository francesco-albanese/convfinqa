import { useForm } from "@tanstack/react-form";
import { Send } from "lucide-react";
import {
	forwardRef,
	type KeyboardEvent,
	useId,
	useImperativeHandle,
	useRef,
} from "react";
import { cn } from "@/lib/utils";

const MAX_CHARS = 32000;
const COUNTER_THRESHOLD = 28000;
const DISABLED_HINT = "Pin a document first";

export type ComposerHandle = {
	setText: (text: string) => void;
};

type ComposerProps = {
	onSend: (text: string) => void;
	disabled?: boolean;
};

export const Composer = forwardRef<ComposerHandle, ComposerProps>(
	function Composer({ onSend, disabled = false }, ref) {
		const textareaRef = useRef<HTMLTextAreaElement | null>(null);
		const hintId = useId();

		const form = useForm({
			defaultValues: { message: "" },
			onSubmit: ({ value }) => {
				const trimmed = value.message.trim();
				if (!trimmed) return;
				onSend(trimmed);
				form.reset();
				resetHeight(textareaRef.current);
			},
		});

		useImperativeHandle(ref, () => ({
			setText: (text: string) => {
				form.setFieldValue("message", text);
				const textarea = textareaRef.current;
				if (!textarea) return;
				textarea.focus();
				textarea.setSelectionRange(text.length, text.length);
				autoGrow(textarea);
			},
		}));

		const submit = () => {
			void form.handleSubmit();
		};

		const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
			const isSubmitChord =
				(event.metaKey || event.ctrlKey) && event.key === "Enter";
			if (!isSubmitChord) return;
			event.preventDefault();
			if (disabled) return;
			submit();
		};

		return (
			<form
				onSubmit={(event) => {
					event.preventDefault();
					submit();
				}}
				className="relative flex flex-col gap-2 rounded-lg border border-border bg-input p-3"
				aria-disabled={disabled}
			>
				<form.Field name="message">
					{(field) => (
						<>
							<textarea
								ref={textareaRef}
								value={field.state.value}
								onChange={(event) => {
									field.handleChange(event.target.value);
									autoGrow(event.currentTarget);
								}}
								onKeyDown={handleKeyDown}
								disabled={disabled}
								maxLength={MAX_CHARS}
								rows={1}
								placeholder={
									disabled
										? DISABLED_HINT
										: "Ask about the pinned document — Cmd+Enter to send"
								}
								aria-label="Message"
								aria-describedby={disabled ? hintId : undefined}
								className={cn(
									"w-full resize-none bg-transparent text-sm leading-6 text-foreground placeholder:text-muted-foreground outline-none",
									"max-h-72 min-h-[1.5rem]",
									disabled && "cursor-not-allowed opacity-60",
								)}
							/>
							<div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
								<div className="flex items-center gap-3">
									{disabled && (
										<span id={hintId} role="note">
											{DISABLED_HINT}
										</span>
									)}
									{field.state.value.length > COUNTER_THRESHOLD && (
										<span
											aria-live="polite"
											className={cn(
												"numeric",
												field.state.value.length >= MAX_CHARS && "text-primary",
											)}
										>
											{field.state.value.length.toLocaleString()} /{" "}
											{MAX_CHARS.toLocaleString()}
										</span>
									)}
								</div>
								<button
									type="submit"
									disabled={disabled || field.state.value.trim() === ""}
									className={cn(
										"inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground",
										"hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
										"disabled:cursor-not-allowed disabled:opacity-50",
									)}
									aria-label="Send message"
								>
									<Send aria-hidden="true" className="size-3.5" />
									Send
								</button>
							</div>
						</>
					)}
				</form.Field>
			</form>
		);
	},
);

function autoGrow(el: HTMLTextAreaElement) {
	el.style.height = "auto";
	el.style.height = `${el.scrollHeight}px`;
}

function resetHeight(el: HTMLTextAreaElement | null) {
	if (!el) return;
	el.style.height = "auto";
}

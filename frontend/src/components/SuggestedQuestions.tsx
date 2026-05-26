import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

type SuggestedQuestionsVariant = "hero" | "followup";

type SuggestedQuestionsProps = {
	questions: ReadonlyArray<string>;
	onSelect: (question: string) => void;
	variant?: SuggestedQuestionsVariant;
};

const HEADINGS: Record<SuggestedQuestionsVariant, string> = {
	hero: "suggested questions",
	followup: "try next",
};

export function SuggestedQuestions({
	questions,
	onSelect,
	variant = "hero",
}: SuggestedQuestionsProps) {
	if (questions.length === 0) return null;

	const isHero = variant === "hero";

	return (
		<section
			aria-label="Suggested questions"
			data-testid="suggested-questions"
			data-variant={variant}
			className={cn(
				"flex flex-col gap-3",
				isHero
					? "mx-auto max-w-2xl items-center py-6 text-center"
					: "items-start pt-4",
			)}
		>
			<p className="flex items-center gap-1.5 text-muted-foreground text-xs uppercase tracking-widest">
				<Sparkles aria-hidden="true" className="size-3.5" />
				{HEADINGS[variant]}
			</p>
			<ul
				className={cn(
					"flex flex-wrap gap-2",
					isHero ? "justify-center" : "justify-start",
				)}
			>
				{questions.map((question) => (
					<li key={question}>
						<button
							type="button"
							onClick={() => onSelect(question)}
							className="rounded-full border border-border bg-background px-3 py-1.5 text-foreground text-sm hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
						>
							{question}
						</button>
					</li>
				))}
			</ul>
		</section>
	);
}

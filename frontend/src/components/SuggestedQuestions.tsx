import { Sparkles } from "lucide-react";

type SuggestedQuestionsProps = {
	questions: ReadonlyArray<string>;
	onSend: (question: string) => void;
};

export function SuggestedQuestions({
	questions,
	onSend,
}: SuggestedQuestionsProps) {
	if (questions.length === 0) return null;

	return (
		<section
			aria-label="Suggested questions"
			data-testid="suggested-questions"
			className="mx-auto flex max-w-2xl flex-col items-center gap-3 py-6 text-center"
		>
			<p className="flex items-center gap-1.5 text-muted-foreground text-xs uppercase tracking-widest">
				<Sparkles aria-hidden="true" className="size-3.5" />
				suggested questions
			</p>
			<ul className="flex flex-wrap justify-center gap-2">
				{questions.map((question) => (
					<li key={question}>
						<button
							type="button"
							onClick={() => onSend(question)}
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

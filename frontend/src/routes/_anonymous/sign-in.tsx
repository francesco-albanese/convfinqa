import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AuthLoadingShell } from "@/components/AuthLoadingShell";
import { useAuth } from "@/lib/auth/AuthProvider";

export const Route = createFileRoute("/_anonymous/sign-in")({
	component: SignInPage,
});

function SignInPage() {
	const { mode, signIn } = useAuth();
	const [redirecting, setRedirecting] = useState(false);

	if (redirecting) {
		return <AuthLoadingShell />;
	}

	const handleSignIn = () => {
		setRedirecting(true);
		window.setTimeout(signIn, 0);
	};

	return (
		<main className="min-h-screen w-screen bg-background text-foreground">
			<div className="mx-auto grid min-h-screen max-w-6xl grid-cols-1 lg:grid-cols-2">
				<aside className="hidden flex-col justify-between px-10 py-12 lg:flex">
					<div className="flex items-center gap-2 font-semibold text-foreground text-sm tracking-tight">
						<span>convfin</span>
						<span aria-hidden="true" className="text-primary">
							·
						</span>
						<span>qa</span>
					</div>
					<div className="flex flex-col gap-6">
						<p className="numeric text-muted-foreground text-xs">
							~/convfinqa › login{" "}
							<span aria-hidden="true" className="text-primary">
								▍
							</span>
						</p>
						<h1 className="text-balance font-semibold text-4xl text-foreground leading-tight tracking-tight">
							Talk to your
							<br />
							financial filings.
						</h1>
						<p className="max-w-md text-muted-foreground text-sm">
							Multi-turn conversational reasoning over earnings reports, 10-Ks
							and annual statements — grounded in the source table you pick.
						</p>
					</div>
					<ul className="flex flex-col gap-2 text-muted-foreground text-xs">
						<li>
							<span className="numeric mr-2 text-primary">$</span> chained
							reasoning · 3,892 dialogues
						</li>
						<li>
							<span className="numeric mr-2 text-primary">$</span> grounded
							answers · cell-level citations
						</li>
						<li>
							<span className="numeric mr-2 text-primary">$</span> full-context
							· no retriever needed
						</li>
					</ul>
				</aside>

				<section
					aria-labelledby="sign-in-heading"
					className="flex items-center justify-center px-6 py-12 sm:px-10"
				>
					<div className="flex w-full max-w-sm flex-col gap-5 rounded-lg border border-border bg-card p-8 shadow-sm">
						<header className="flex flex-col gap-1">
							<p className="text-muted-foreground text-xs uppercase tracking-widest">
								Sign in
							</p>
							<h2
								id="sign-in-heading"
								className="font-semibold text-2xl text-foreground tracking-tight"
							>
								Welcome back
							</h2>
							<p className="text-muted-foreground text-sm">
								Continue where you left off.
							</p>
						</header>

						<button
							type="button"
							onClick={handleSignIn}
							disabled={redirecting}
							className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md border border-border bg-input font-medium text-foreground text-sm hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
						>
							{mode === "remote" ? <GoogleGlyph /> : null}
							{mode === "local" ? "Continue locally" : "Continue with Google"}
						</button>

						<p className="text-center text-[11px] text-muted-foreground">
							{mode === "local"
								? "local development session"
								: "secured by AWS Cognito · SSO via Google OAuth 2.0"}
						</p>
					</div>
				</section>
			</div>
		</main>
	);
}

function GoogleGlyph() {
	return (
		<svg
			aria-hidden="true"
			viewBox="0 0 24 24"
			className="size-4"
			focusable="false"
		>
			<path
				fill="#EA4335"
				d="M12 10.2v3.9h5.5c-.2 1.3-1.7 3.8-5.5 3.8-3.3 0-6-2.7-6-6.1S8.7 5.8 12 5.8c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.7 3.1 14.5 2 12 2 6.9 2 2.8 6.1 2.8 11.8S6.9 21.5 12 21.5c6.9 0 9.6-4.8 9.6-9.3 0-.6-.1-1.1-.2-1.6H12z"
			/>
			<path
				fill="#4285F4"
				d="M21.6 12.2c0-.6-.1-1.1-.2-1.6H12v3.6h5.5c-.2 1.3-1.7 3.8-5.5 3.8v3.5c3.4 0 6.4-1.1 8.4-3 1.7-1.6 2.6-3.9 2.6-6.3z"
				opacity=".3"
			/>
		</svg>
	);
}

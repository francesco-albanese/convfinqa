import type { CSSProperties } from "react";

export function AuthLoadingShell() {
	return (
		<div
			data-testid="auth-loading-shell"
			className="authed-grid h-screen w-screen overflow-hidden bg-background text-foreground"
			style={{ "--sb-w": "280px" } as CSSProperties}
		>
			<aside className="hidden h-full border-border border-r bg-card lg:block">
				<div className="flex h-full flex-col gap-4 p-4">
					<div className="h-9 w-9 rounded-md bg-secondary" />
					<div className="space-y-2">
						<div className="h-3 w-24 rounded bg-secondary" />
						<div className="h-8 rounded-md bg-secondary/70" />
					</div>
					<div className="space-y-2">
						<div className="h-3 w-28 rounded bg-secondary" />
						<div className="h-8 rounded-md bg-secondary/70" />
						<div className="h-8 rounded-md bg-secondary/50" />
						<div className="h-8 rounded-md bg-secondary/40" />
					</div>
					<div className="mt-auto h-10 rounded-md bg-secondary/70" />
				</div>
			</aside>
			<main className="flex min-w-0 flex-col overflow-hidden">
				<div className="flex h-14 items-center gap-3 border-border border-b px-4 lg:hidden">
					<div className="h-9 w-9 rounded-md bg-secondary" />
					<div className="h-3 w-32 rounded bg-secondary" />
				</div>
				<div className="flex flex-1 flex-col justify-end gap-4 p-4 sm:p-6">
					<div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-4">
						<div className="h-4 w-40 rounded bg-secondary" />
						<div className="h-24 rounded-md border border-border bg-card" />
						<div className="h-24 rounded-md border border-border bg-card/70" />
					</div>
					<div className="mx-auto w-full max-w-3xl rounded-md border border-border bg-card p-3">
						<div className="h-11 rounded bg-secondary" />
					</div>
				</div>
			</main>
			<aside className="hidden h-full border-border border-l bg-card lg:block">
				<div className="flex h-full flex-col gap-4 p-4">
					<div className="h-4 w-36 rounded bg-secondary" />
					<div className="aspect-video rounded-md bg-secondary/70" />
					<div className="space-y-2">
						<div className="h-3 rounded bg-secondary/70" />
						<div className="h-3 w-5/6 rounded bg-secondary/60" />
						<div className="h-3 w-2/3 rounded bg-secondary/50" />
					</div>
				</div>
			</aside>
			<div role="status" aria-live="polite" className="sr-only">
				Loading session
			</div>
		</div>
	);
}

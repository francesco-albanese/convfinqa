import { type ReactNode, useCallback, useEffect, useState } from "react";
import { checkHealth } from "@/lib/api/healthcheck";

type Status = "pending" | "ready" | "error";

type Props = {
	children: ReactNode;
};

export function WakeupGate({ children }: Props) {
	const [status, setStatus] = useState<Status>("pending");

	const wake = useCallback(() => {
		setStatus("pending");
		checkHealth()
			.then(() => setStatus("ready"))
			.catch(() => setStatus("error"));
	}, []);

	useEffect(() => {
		wake();
	}, [wake]);

	if (status === "ready") return <>{children}</>;

	if (status === "error") {
		return (
			<div className="flex min-h-screen flex-col items-center justify-center gap-4">
				<p className="text-muted-foreground text-sm">
					Infrastructure is taking too long to respond.
				</p>
				<button
					type="button"
					onClick={wake}
					className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
				>
					Retry
				</button>
			</div>
		);
	}

	return (
		<div className="flex min-h-screen items-center justify-center">
			<p
				className="text-muted-foreground animate-pulse text-sm"
				data-testid="wakeup-loader"
			>
				Waking up infrastructure...
			</p>
		</div>
	);
}

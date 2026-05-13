import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { readPersistedAuthUserId } from "@/lib/auth/AuthProvider";

export const Route = createFileRoute("/_anonymous")({
	beforeLoad: () => {
		if (readPersistedAuthUserId() !== null) {
			throw redirect({ to: "/app" });
		}
	},
	component: AnonymousLayout,
});

function AnonymousLayout() {
	return <Outlet />;
}

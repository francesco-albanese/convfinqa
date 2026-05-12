import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/_authed")({
	component: AuthedLayout,
});

function AuthedLayout() {
	return <Outlet />;
}

import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/_anonymous")({
	component: AnonymousLayout,
});

function AnonymousLayout() {
	return <Outlet />;
}

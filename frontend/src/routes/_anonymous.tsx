import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth/AuthProvider";

export const Route = createFileRoute("/_anonymous")({
	component: AnonymousLayout,
});

function AnonymousLayout() {
	const { status } = useAuth();
	const navigate = useNavigate();

	useEffect(() => {
		if (status === "authed") {
			void navigate({ to: "/app", replace: true });
		}
	}, [status, navigate]);

	return <Outlet />;
}

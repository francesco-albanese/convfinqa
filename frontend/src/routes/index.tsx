import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth/AuthProvider";

export const Route = createFileRoute("/")({
	component: RootRedirect,
});

function RootRedirect() {
	const { status } = useAuth();
	const navigate = useNavigate();

	useEffect(() => {
		if (status === "authed") {
			void navigate({ to: "/app", replace: true });
		} else if (status === "unauthed") {
			void navigate({ to: "/sign-in", replace: true });
		}
	}, [status, navigate]);

	return null;
}

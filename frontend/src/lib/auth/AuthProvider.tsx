import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useEffect,
	useMemo,
	useState,
} from "react";
import { apiFetch, registerUnauthHandler } from "@/lib/api/client";

export type AuthStatus = "loading" | "authed" | "unauthed";

export type AuthContextValue = {
	userId: string | null;
	email: string | null;
	status: AuthStatus;
	mode: "local" | "remote";
	signIn: () => void;
	signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
	const [mode, setMode] = useState<"local" | "remote">("remote");
	const [userId, setUserId] = useState<string | null>(null);
	const [email, setEmail] = useState<string | null>(null);
	const [status, setStatus] = useState<AuthStatus>("loading");

	const handleUnauthed = useCallback(() => {
		setUserId(null);
		setEmail(null);
		setStatus("unauthed");
	}, []);

	useEffect(() => {
		return registerUnauthHandler(handleUnauthed);
	}, [handleUnauthed]);

	useEffect(() => {
		let ignore = false;
		apiFetch("/api/v1/me")
			.then(async (res) => {
				if (ignore) return;
				if (res.ok) {
					const data = (await res.json()) as {
						user_id: string;
						email: string | null;
					};
					setUserId(data.user_id);
					setEmail(data.email);
					setMode(
						res.headers.get("X-Auth-Mode") === "local" ? "local" : "remote",
					);
					setStatus("authed");
				} else {
					setStatus("unauthed");
				}
			})
			.catch(() => {
				if (!ignore) setStatus("unauthed");
			});
		return () => {
			ignore = true;
		};
	}, []);

	const signIn = useCallback(() => {
		window.location.href = mode === "local" ? "/app" : "/api/auth/login";
	}, [mode]);

	const signOut = useCallback(async () => {
		if (mode === "remote") {
			await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
		}
		setUserId(null);
		setEmail(null);
		setStatus("unauthed");
	}, [mode]);

	const value = useMemo<AuthContextValue>(
		() => ({ userId, email, status, mode, signIn, signOut }),
		[userId, email, status, mode, signIn, signOut],
	);

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
	const value = useContext(AuthContext);
	if (value === null) {
		throw new Error("useAuth must be used within an <AuthProvider>");
	}
	return value;
}

export function useAuthedUserId(): string {
	const { userId, status } = useAuth();
	if (status === "loading") {
		return "";
	}
	if (userId === null) {
		throw new Error(
			"useAuthedUserId requires an authenticated session; call only inside the /_authed route subtree.",
		);
	}
	return userId;
}

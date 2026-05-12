import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useMemo,
	useState,
} from "react";

export const AUTH_STORAGE_KEY = "auth.userId";
const DEV_USER_PREFIX = "dev-user-";

export type AuthContextValue = {
	userId: string | null;
	signIn: () => void;
	signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readPersistedUserId(): string | null {
	try {
		const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
		return raw?.startsWith(DEV_USER_PREFIX) ? raw : null;
	} catch {
		return null;
	}
}

function persistUserId(userId: string | null): void {
	try {
		if (userId === null) {
			window.localStorage.removeItem(AUTH_STORAGE_KEY);
		} else {
			window.localStorage.setItem(AUTH_STORAGE_KEY, userId);
		}
	} catch {
		// Quota exceeded or storage blocked — silently drop.
	}
}

export function AuthProvider({ children }: { children: ReactNode }) {
	const [userId, setUserId] = useState<string | null>(readPersistedUserId);

	const signIn = useCallback(() => {
		const next = `${DEV_USER_PREFIX}${crypto.randomUUID()}`;
		persistUserId(next);
		setUserId(next);
	}, []);

	const signOut = useCallback(() => {
		persistUserId(null);
		setUserId(null);
	}, []);

	const value = useMemo<AuthContextValue>(
		() => ({ userId, signIn, signOut }),
		[userId, signIn, signOut],
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

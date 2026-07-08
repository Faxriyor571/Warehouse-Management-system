import * as React from "react";

import { authService } from "@/services/auth";
import { tokenStorage } from "@/lib/token-storage";
import type { User } from "@/types/auth";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string, companySlug?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    const accessToken = tokenStorage.getAccess();
    if (!accessToken) {
      setIsLoading(false);
      return;
    }
    authService
      .me()
      .then(setUser)
      .catch(() => tokenStorage.clear())
      .finally(() => setIsLoading(false));
  }, []);

  const login = React.useCallback(
    async (username: string, password: string, companySlug?: string) => {
      const token = await authService.login(username, password, companySlug);
      tokenStorage.set(token.access_token, token.refresh_token);
      const me = await authService.me();
      setUser(me);
    },
    []
  );

  const logout = React.useCallback(async () => {
    const refreshToken = tokenStorage.getRefresh();
    try {
      await authService.logout(refreshToken ?? undefined);
    } catch {
      // Best-effort: proceed with local logout even if the request fails.
    }
    tokenStorage.clear();
    setUser(null);
  }, []);

  const value = React.useMemo<AuthContextValue>(
    () => ({ user, isAuthenticated: user !== null, isLoading, login, logout }),
    [user, isLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

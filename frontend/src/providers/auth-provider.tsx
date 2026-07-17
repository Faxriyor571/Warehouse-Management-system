import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";

import { authService } from "@/services/auth";
import { companyService } from "@/services/company";
import { tokenStorage } from "@/lib/token-storage";
import { hasPerm, type Perm } from "@/lib/permissions";
import type { User } from "@/types/auth";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string, companySlug?: string) => Promise<void>;
  logout: () => Promise<void>;
  /** System Owner only: enter a support session, viewing a company as its CEO. */
  enterSupportSession: (companyId: number) => Promise<void>;
  /** Return to the System Owner's own session from an active support session. */
  exitSupportSession: () => Promise<void>;
  /** Whether the current user holds the given permission (see lib/permissions.ts). */
  hasPerm: (perm: Perm) => boolean;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const queryClient = useQueryClient();

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
      // Every query key (["stores"], ["products"], ["dashboard"], ...) is
      // identity-agnostic — with the global staleTime: 0, an uncleared
      // cache would flash the *previous* session's data on mount before
      // the fresh fetch resolves. Clearing on every identity transition
      // (also below) guarantees a logged-in user never sees so much as a
      // flicker of another account's — or another company's — data.
      queryClient.clear();
      const me = await authService.me();
      setUser(me);
    },
    [queryClient]
  );

  const logout = React.useCallback(async () => {
    const refreshToken = tokenStorage.getRefresh();
    try {
      await authService.logout(refreshToken ?? undefined);
    } catch {
      // Best-effort: proceed with local logout even if the request fails.
    }
    tokenStorage.clear();
    queryClient.clear();
    setUser(null);
  }, [queryClient]);

  const enterSupportSession = React.useCallback(
    async (companyId: number) => {
      const result = await companyService.startSupportSession(companyId);
      tokenStorage.enterSupportSession(result.access_token);
      queryClient.clear();
      const me = await authService.me();
      setUser(me);
    },
    [queryClient]
  );

  const exitSupportSession = React.useCallback(async () => {
    tokenStorage.exitSupportSession();
    queryClient.clear();
    const me = await authService.me();
    setUser(me);
  }, [queryClient]);

  const checkPerm = React.useCallback((perm: Perm) => hasPerm(user, perm), [user]);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isLoading,
      login,
      logout,
      enterSupportSession,
      exitSupportSession,
      hasPerm: checkPerm,
    }),
    [user, isLoading, login, logout, enterSupportSession, exitSupportSession, checkPerm]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

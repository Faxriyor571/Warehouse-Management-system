const ACCESS_KEY = "wms_access_token";
const REFRESH_KEY = "wms_refresh_token";
// Stashed here while a System Owner support session is active, so exiting
// (or the support session's access token simply expiring) can restore the
// owner's own session instead of forcing a full re-login.
const OWNER_ACCESS_KEY = "wms_owner_access_token";
const OWNER_REFRESH_KEY = "wms_owner_refresh_token";

export const tokenStorage = {
  getAccess: (): string | null => localStorage.getItem(ACCESS_KEY),
  getRefresh: (): string | null => localStorage.getItem(REFRESH_KEY),
  set: (accessToken: string, refreshToken: string): void => {
    localStorage.setItem(ACCESS_KEY, accessToken);
    localStorage.setItem(REFRESH_KEY, refreshToken);
  },
  clear: (): void => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(OWNER_ACCESS_KEY);
    localStorage.removeItem(OWNER_REFRESH_KEY);
  },

  hasOwnerSession: (): boolean => localStorage.getItem(OWNER_ACCESS_KEY) !== null,

  /** Stash the current (System Owner) session and switch to a support-session access token. */
  enterSupportSession: (supportAccessToken: string): void => {
    const access = localStorage.getItem(ACCESS_KEY);
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (access) localStorage.setItem(OWNER_ACCESS_KEY, access);
    if (refresh) localStorage.setItem(OWNER_REFRESH_KEY, refresh);
    localStorage.setItem(ACCESS_KEY, supportAccessToken);
    // Support-session tokens are access-only (see company_service.
    // start_support_session) — clear any stale refresh token so the http
    // interceptor doesn't try to silently refresh into the owner's own
    // unscoped session mid-support-session.
    localStorage.removeItem(REFRESH_KEY);
  },

  /** Restore the stashed System Owner session after a support session ends. */
  exitSupportSession: (): void => {
    const ownerAccess = localStorage.getItem(OWNER_ACCESS_KEY);
    const ownerRefresh = localStorage.getItem(OWNER_REFRESH_KEY);
    if (ownerAccess) localStorage.setItem(ACCESS_KEY, ownerAccess);
    else localStorage.removeItem(ACCESS_KEY);
    if (ownerRefresh) localStorage.setItem(REFRESH_KEY, ownerRefresh);
    else localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(OWNER_ACCESS_KEY);
    localStorage.removeItem(OWNER_REFRESH_KEY);
  },
};

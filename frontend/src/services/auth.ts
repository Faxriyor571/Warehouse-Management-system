import { http } from "@/lib/http";
import type { Token, User } from "@/types/auth";

export const authService = {
  async login(username: string, password: string, companySlug?: string): Promise<Token> {
    const body = new URLSearchParams();
    body.set("username", username);
    body.set("password", password);
    if (companySlug) body.set("company_slug", companySlug);

    const { data } = await http.post<Token>("/auth/login", body, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return data;
  },

  async refresh(refreshToken: string): Promise<Token> {
    const { data } = await http.post<Token>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return data;
  },

  async logout(refreshToken?: string): Promise<void> {
    await http.post("/auth/logout", refreshToken ? { refresh_token: refreshToken } : undefined);
  },

  async me(): Promise<User> {
    const { data } = await http.get<User>("/auth/me");
    return data;
  },
};

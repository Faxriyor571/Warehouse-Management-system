import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { tokenStorage } from "./token-storage";
import type { Token } from "@/types/auth";

export const http = axios.create({
  baseURL: "/api/v1",
});

http.interceptors.request.use((config) => {
  const accessToken = tokenStorage.getAccess();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

let refreshPromise: Promise<Token> | null = null;

async function refreshAccessToken(): Promise<Token> {
  const refreshToken = tokenStorage.getRefresh();
  if (!refreshToken) throw new Error("No refresh token");

  const { data } = await axios.post<Token>("/api/v1/auth/refresh", {
    refresh_token: refreshToken,
  });
  tokenStorage.set(data.access_token, data.refresh_token);
  return data;
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableConfig | undefined;
    const isAuthEndpoint = config?.url?.includes("/auth/");

    if (error.response?.status !== 401 || !config || config._retried || isAuthEndpoint) {
      throw error;
    }

    config._retried = true;

    try {
      refreshPromise ??= refreshAccessToken();
      const token = await refreshPromise;
      config.headers.Authorization = `Bearer ${token.access_token}`;
      return http(config);
    } catch (refreshError) {
      tokenStorage.clear();
      window.location.href = "/login";
      throw refreshError;
    } finally {
      refreshPromise = null;
    }
  }
);

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  if (error instanceof Error) return error.message;
  return "Xatolik yuz berdi. Qaytadan urinib ko'ring.";
}

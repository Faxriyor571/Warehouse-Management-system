import * as React from "react";
import axios from "axios";
import { AlertOctagon, RotateCw, ShieldAlert } from "lucide-react";

import { cn } from "@/lib/utils";
import { getErrorMessage } from "@/lib/http";

export interface ErrorStateProps {
  /** The caught query/mutation error, if available. A 403 renders a distinct
   * permission-denied state (no retry button — retrying won't change the
   * caller's permissions) instead of the generic message. */
  error?: unknown;
  title?: string;
  description?: React.ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
  compact?: boolean;
}

export function ErrorState({
  error,
  title,
  description,
  onRetry,
  retryLabel = "Qaytadan urinish",
  className,
  compact,
}: ErrorStateProps) {
  const isForbidden = axios.isAxiosError(error) && error.response?.status === 403;

  const resolvedTitle = title ?? (isForbidden ? "Ruxsat berilmagan" : "Xatolik yuz berdi");
  const resolvedDescription =
    description ?? (isForbidden ? getErrorMessage(error) : "Kutilmagan xatolik yuz berdi. Qaytadan urinib ko'ring.");
  // A 403 won't resolve by retrying with the same session — only offer retry
  // for transient/unknown failures, unless the caller explicitly forces it.
  const showRetry = onRetry && !isForbidden;

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center text-center",
        compact ? "gap-2 p-6" : "gap-3 p-12",
        className
      )}
    >
      <div
        className={cn(
          "flex items-center justify-center rounded-2xl bg-destructive/10 text-destructive ring-1 ring-destructive/15",
          compact ? "size-11" : "size-14"
        )}
      >
        {isForbidden ? (
          <ShieldAlert className={compact ? "size-5" : "size-6"} strokeWidth={1.75} aria-hidden />
        ) : (
          <AlertOctagon className={compact ? "size-5" : "size-6"} strokeWidth={1.75} aria-hidden />
        )}
      </div>
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-foreground">{resolvedTitle}</h3>
        {resolvedDescription ? (
          <p className="mx-auto max-w-sm text-sm text-muted-foreground">{resolvedDescription}</p>
        ) : null}
      </div>
      {showRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1.5 inline-flex items-center gap-2 rounded-lg border border-input bg-card px-3 py-1.5 text-sm font-medium shadow-xs transition-colors hover:bg-accent"
        >
          <RotateCw className="size-4" />
          {retryLabel}
        </button>
      ) : null}
    </div>
  );
}

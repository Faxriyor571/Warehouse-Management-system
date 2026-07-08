import * as React from "react";
import { AlertOctagon, RotateCw } from "lucide-react";

import { cn } from "@/lib/utils";

export interface ErrorStateProps {
  title?: string;
  description?: React.ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
  compact?: boolean;
}

export function ErrorState({
  title = "Xatolik yuz berdi",
  description = "Kutilmagan xatolik yuz berdi. Qaytadan urinib ko'ring.",
  onRetry,
  retryLabel = "Qaytadan urinish",
  className,
  compact,
}: ErrorStateProps) {
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
          "flex items-center justify-center rounded-full bg-destructive/10 text-destructive",
          compact ? "size-10" : "size-14"
        )}
      >
        <AlertOctagon className={compact ? "size-5" : "size-7"} aria-hidden />
      </div>
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {description ? (
          <p className="mx-auto max-w-sm text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 inline-flex items-center gap-2 rounded-md border border-input px-3 py-1.5 text-sm font-medium hover:bg-accent"
        >
          <RotateCw className="size-4" />
          {retryLabel}
        </button>
      ) : null}
    </div>
  );
}

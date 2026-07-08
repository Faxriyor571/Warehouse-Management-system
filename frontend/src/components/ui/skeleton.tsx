import * as React from "react";

import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-muted", className)} aria-hidden {...props} />;
}

function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={cn("h-4", i === lines - 1 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  );
}

/** SkeletonCard — mirrors the Dashboard stat-card layout (label, big value, icon chip). */
function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-start justify-between gap-4 rounded-xl border p-5", className)}>
      <div className="space-y-2.5">
        <Skeleton className="h-3.5 w-24" />
        <Skeleton className="h-7 w-28" />
        <Skeleton className="h-3 w-16" />
      </div>
      <Skeleton className="size-10 shrink-0 rounded-lg" />
    </div>
  );
}

/** TableSkeleton — the standard loading placeholder for a list page's table. */
function TableSkeleton({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-3 p-6", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export { Skeleton, SkeletonText, SkeletonCard, TableSkeleton };

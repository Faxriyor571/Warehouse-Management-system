import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/formatters";
import type { PageMeta } from "@/types/common";
import { Button } from "./button";

export interface PaginationProps {
  meta: PageMeta;
  onPageChange: (page: number) => void;
  className?: string;
}

/** Pagination — standard footer for a TableCard, driven by the backend's PageMeta. */
export function Pagination({ meta, onPageChange, className }: PaginationProps) {
  if (meta.total === 0) return null;

  const from = (meta.page - 1) * meta.page_size + 1;
  const to = Math.min(meta.page * meta.page_size, meta.total);

  return (
    <div
      className={cn(
        "flex flex-col gap-3 border-t border-border/70 px-5 py-3 sm:flex-row sm:items-center sm:justify-between",
        className
      )}
    >
      <p className="text-xs text-muted-foreground">
        <span className="font-medium text-foreground">
          {formatNumber(from)}–{formatNumber(to)}
        </span>{" "}
        / {formatNumber(meta.total)} ta natija
      </p>
      <div className="flex items-center gap-1.5">
        <Button
          variant="outline"
          size="sm"
          disabled={!meta.has_prev}
          onClick={() => onPageChange(meta.page - 1)}
        >
          <ChevronLeft className="size-4" />
          Oldingi
        </Button>
        <span className="px-1.5 text-xs tabular-nums text-muted-foreground">
          {meta.page} / {meta.total_pages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={!meta.has_next}
          onClick={() => onPageChange(meta.page + 1)}
        >
          Keyingi
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}

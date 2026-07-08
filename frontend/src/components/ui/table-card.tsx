import * as React from "react";

import { cn } from "@/lib/utils";

/** TableCard — the standard elevated panel wrapper for a list page's table/toolbar. */
const TableCard = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("overflow-hidden rounded-xl border border-border/70 bg-card shadow-panel", className)}
      {...props}
    />
  )
);
TableCard.displayName = "TableCard";

export { TableCard };

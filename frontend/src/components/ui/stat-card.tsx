import * as React from "react";

import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

const statToneClass = {
  primary: "bg-primary/10 text-primary",
  success: "bg-success/10 text-success",
  warning: "bg-warning/15 text-warning",
  destructive: "bg-destructive/10 text-destructive",
} as const;

export function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ComponentType<{ className?: string }>;
  tone: keyof typeof statToneClass;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0 space-y-1.5">
          <p className="truncate text-sm font-medium text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold leading-tight tracking-tight text-foreground tabular-nums text-balance">{value}</p>
          {sub ? <p className="truncate text-xs text-muted-foreground">{sub}</p> : null}
        </div>
        <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-lg", statToneClass[tone])}>
          <Icon className="size-5" />
        </div>
      </CardContent>
    </Card>
  );
}

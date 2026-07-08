import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DollarSign, Receipt, ShoppingCart, Users } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatCurrency, formatDateTime, formatNumber } from "@/lib/formatters";
import { dashboardService } from "@/services/dashboard";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton, SkeletonCard } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

const CURRENCY = "UZS";

export default function DashboardPage() {
  const query = useQuery({ queryKey: ["dashboard"], queryFn: dashboardService.getStats });
  const stats = query.data;

  return (
    <ContentContainer>
      <PageHeader
        title="Boshqaruv paneli"
        description={
          stats
            ? stats.scope === "company"
              ? "Barcha do'konlar bo'yicha umumiy ko'rinish."
              : "Do'koningiz bo'yicha umumiy ko'rinish."
            : undefined
        }
      />

      {query.isError ? (
        <ErrorState error={query.error} className="mt-6" onRetry={() => void query.refetch()} />
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {query.isLoading || !stats ? (
              Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
            ) : (
              <>
                <StatCard
                  label="Bugungi savdolar"
                  icon={ShoppingCart}
                  tone="primary"
                  value={formatCurrency(stats.today_sales_total, CURRENCY)}
                  sub={`${formatNumber(stats.today_sales_count)} ta savdo`}
                />
                <StatCard
                  label="Oylik daromad"
                  icon={DollarSign}
                  tone="success"
                  value={formatCurrency(stats.month_revenue, CURRENCY)}
                />
                <StatCard
                  label="Oylik xarajatlar"
                  icon={Receipt}
                  tone="warning"
                  value={formatCurrency(stats.month_expenses, CURRENCY)}
                />
                <StatCard
                  label="Qarzdorlar"
                  icon={Users}
                  tone="destructive"
                  value={formatNumber(stats.debtors_count)}
                  sub={formatCurrency(stats.debtors_total, CURRENCY)}
                />
              </>
            )}
          </div>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Savdolar</CardTitle>
              <CardDescription>Kunlik jami</CardDescription>
            </CardHeader>
            <CardContent>
              {query.isLoading || !stats ? (
                <Skeleton className="h-72 w-full" />
              ) : (stats.sales_chart ?? []).length === 0 ? (
                <EmptyState compact title="Hozircha savdo ma'lumotlari yo'q" />
              ) : (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={(stats.sales_chart ?? []).map((p) => ({ label: p.label, value: Number(p.value) }))}
                      margin={{ left: -16, right: 8, top: 8 }}
                    >
                      <defs>
                        <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                      <XAxis dataKey="label" tickLine={false} axisLine={false} className="text-xs" stroke="hsl(var(--muted-foreground))" />
                      <YAxis tickLine={false} axisLine={false} className="text-xs" stroke="hsl(var(--muted-foreground))" />
                      <RechartsTooltip
                        cursor={{ stroke: "hsl(var(--primary))", strokeWidth: 1, strokeDasharray: "4 4" }}
                        contentStyle={{
                          background: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "0.75rem",
                          fontSize: "0.8125rem",
                          color: "hsl(var(--popover-foreground))",
                          boxShadow: "0 8px 24px -4px rgb(15 23 42 / 0.12)",
                        }}
                        formatter={(value: number) => formatCurrency(value, CURRENCY)}
                      />
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2.5}
                        fill="url(#fill)"
                        activeDot={{ r: 4, strokeWidth: 2, stroke: "hsl(var(--card))" }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Eng ko'p sotilgan mahsulotlar</CardTitle>
                <CardDescription>Daromad bo'yicha</CardDescription>
              </CardHeader>
              <CardContent className="p-2 pt-0">
                {query.isLoading || !stats ? (
                  <Skeleton className="m-3 h-48" />
                ) : (stats.top_products ?? []).length === 0 ? (
                  <EmptyState compact title="Hozircha mahsulot sotuvlari yo'q" />
                ) : (
                  <ul>
                    {stats.top_products.map((product, i) => (
                      <li
                        key={product.product_id}
                        className="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-accent/60"
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <RankBadge rank={i + 1} />
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-foreground">{product.name}</p>
                            <p className="text-xs text-muted-foreground">{formatNumber(product.quantity_sold)} ta sotildi</p>
                          </div>
                        </div>
                        <span className="shrink-0 text-sm font-semibold tabular-nums text-foreground">
                          {formatCurrency(product.revenue, CURRENCY)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Eng ko'p qarzdorlar</CardTitle>
                <CardDescription>Qolgan qarz bo'yicha</CardDescription>
              </CardHeader>
              <CardContent className="p-2 pt-0">
                {query.isLoading || !stats ? (
                  <Skeleton className="m-3 h-48" />
                ) : (stats.top_debtors ?? []).length === 0 ? (
                  <EmptyState compact title="Ochiq qarzlar yo'q" />
                ) : (
                  <ul>
                    {stats.top_debtors.map((debtor, i) => (
                      <li
                        key={debtor.customer_id}
                        className="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-accent/60"
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <RankBadge rank={i + 1} />
                          <p className="truncate text-sm font-medium text-foreground">{debtor.full_name}</p>
                        </div>
                        <span className="shrink-0 text-sm font-semibold tabular-nums text-destructive">
                          {formatCurrency(debtor.remaining, CURRENCY)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>So'nggi amaliyotlar</CardTitle>
              <CardDescription>Oxirgi savdolar va kirim hujjatlari</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {query.isLoading || !stats ? (
                <Skeleton className="m-6 h-48" />
              ) : (stats.recent_operations ?? []).length === 0 ? (
                <EmptyState compact title="So'nggi amaliyotlar yo'q" />
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead>Turi</TableHead>
                        <TableHead>Hujjat raqami</TableHead>
                        <TableHead>Sana</TableHead>
                        <TableHead className="text-right">Summa</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {stats.recent_operations.map((op, i) => (
                        <TableRow key={i}>
                          <TableCell>
                            <Badge variant={op.type === "sale" ? "success" : "info"}>
                              {op.type === "sale" ? "Savdo" : "Kirim"}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-medium">{op.reference}</TableCell>
                          <TableCell className="text-muted-foreground">{formatDateTime(op.date)}</TableCell>
                          <TableCell className="text-right tabular-nums font-medium">
                            {formatCurrency(op.amount, CURRENCY)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </ContentContainer>
  );
}

const statToneClass = {
  primary: "bg-primary/10 text-primary",
  success: "bg-success/10 text-success",
  warning: "bg-warning/15 text-warning",
  destructive: "bg-destructive/10 text-destructive",
} as const;

function StatCard({
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
      <CardContent className="flex items-start justify-between gap-4 p-5">
        <div className="min-w-0 space-y-1.5">
          <p className="truncate text-sm font-medium text-muted-foreground">{label}</p>
          <p className="text-[26px] font-semibold leading-none tracking-tight text-foreground">{value}</p>
          {sub ? <p className="text-xs text-muted-foreground">{sub}</p> : null}
        </div>
        <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-lg", statToneClass[tone])}>
          <Icon className="size-5" />
        </div>
      </CardContent>
    </Card>
  );
}

function RankBadge({ rank }: { rank: number }) {
  return (
    <span
      className={cn(
        "flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold tabular-nums",
        rank === 1
          ? "bg-warning/15 text-warning"
          : rank === 2
            ? "bg-muted-foreground/15 text-muted-foreground"
            : rank === 3
              ? "bg-primary/10 text-primary"
              : "bg-muted text-muted-foreground"
      )}
    >
      {rank}
    </span>
  );
}

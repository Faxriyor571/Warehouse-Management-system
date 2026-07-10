import * as React from "react";
import { useNavigate } from "react-router-dom";
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
import { AlertTriangle, Building2, DollarSign, LogIn, PlusCircle, Receipt, ShoppingCart, TrendingUp } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { formatDate, formatDateTime, formatMoney, formatNumber } from "@/lib/formatters";
import { getErrorMessage } from "@/lib/http";
import { useAuth } from "@/providers/auth-provider";
import { companyService } from "@/services/company";
import { dashboardService } from "@/services/dashboard";
import { reportService } from "@/services/report";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton, SkeletonCard } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

export default function DashboardPage() {
  const { user } = useAuth();
  // The System Owner has no financial/warehouse data of their own (SRS
  // §3.1) — their dashboard is the platform view, not the tenant one.
  if (user?.role === "super_admin") return <PlatformDashboard />;
  return <TenantDashboard />;
}

function TenantDashboard() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["dashboard"], queryFn: dashboardService.getStats });
  const stats = query.data;

  // Store-scoping for Seller (and company-wide for CEO) is already enforced
  // server-side by this endpoint's existing scope resolution — no extra
  // filtering needed here. Detailed debt stats (overdue/due-today/active/
  // paid) live only on the Debts page now — this is just the top-of-page
  // alert, so CEO/Seller still see it immediately after login.
  const debtReportQuery = useQuery({ queryKey: ["reports", "debts", "dashboard-alert"], queryFn: () => reportService.debts({}) });

  const overdueBucket = debtReportQuery.data?.by_status.find((b) => b.status === "overdue");
  const overdueCount = overdueBucket?.count ?? 0;
  const overdueTotal = overdueBucket?.remaining ?? "0";
  const netProfit = stats ? Number(stats.month_revenue) - Number(stats.month_expenses) : 0;

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
          {overdueCount > 0 ? (
            <button
              type="button"
              onClick={() => navigate("/debts?status=overdue")}
              className="mt-6 flex w-full items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-left transition-colors hover:bg-destructive/10"
            >
              <AlertTriangle className="size-5 shrink-0 text-destructive" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-destructive">
                  {formatNumber(overdueCount)} ta qarz muddati o'tgan — jami {formatMoney(overdueTotal)}
                </p>
                <p className="text-xs text-destructive/80">Batafsil ko'rish uchun bosing.</p>
              </div>
            </button>
          ) : null}

          <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {query.isLoading || !stats ? (
              Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
            ) : (
              <>
                <StatCard
                  label="Bugungi savdolar"
                  icon={ShoppingCart}
                  tone="primary"
                  value={formatMoney(stats.today_sales_total)}
                  sub={`${formatNumber(stats.today_sales_count)} ta savdo`}
                />
                <StatCard
                  label="Oylik daromad"
                  icon={DollarSign}
                  tone="success"
                  value={formatMoney(stats.month_revenue)}
                />
                <StatCard
                  label="Oylik xarajatlar"
                  icon={Receipt}
                  tone="warning"
                  value={formatMoney(stats.month_expenses)}
                />
                <StatCard
                  label="Sof foyda"
                  icon={TrendingUp}
                  tone={netProfit >= 0 ? "success" : "destructive"}
                  value={formatMoney(netProfit)}
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
                      margin={{ left: 0, right: 8, top: 8 }}
                    >
                      <defs>
                        <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                      <XAxis dataKey="label" tickLine={false} axisLine={false} className="text-xs" stroke="hsl(var(--muted-foreground))" />
                      <YAxis
                        tickLine={false}
                        axisLine={false}
                        width={100}
                        tickFormatter={(v: number) => formatMoney(v)}
                        className="text-xs"
                        stroke="hsl(var(--muted-foreground))"
                      />
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
                        labelFormatter={(label: string) => formatDate(label)}
                        formatter={(value: number) => [formatMoney(value), "Savdo"]}
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
                          {formatMoney(product.revenue)}
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
                          {formatMoney(debtor.remaining)}
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
                            {formatMoney(op.amount)}
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

function PlatformDashboard() {
  const navigate = useNavigate();
  const { enterSupportSession } = useAuth();
  const [enteringId, setEnteringId] = React.useState<number | null>(null);

  const query = useQuery({ queryKey: ["companies", "platform-dashboard"], queryFn: () => companyService.list({ page_size: 100 }) });
  const companies = query.data?.items ?? [];
  const activeCount = companies.filter((c) => c.status === "active").length;
  const suspendedCount = companies.filter((c) => c.status === "suspended").length;
  const recent = [...companies].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 5);

  const onEnter = async (companyId: number) => {
    setEnteringId(companyId);
    try {
      await enterSupportSession(companyId);
      navigate("/", { replace: true });
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setEnteringId(null);
    }
  };

  return (
    <ContentContainer>
      <PageHeader
        title="Boshqaruv paneli"
        description="Platformadagi barcha kompaniyalar bo'yicha umumiy ko'rinish."
        actions={
          <Button onClick={() => navigate("/companies")}>
            <PlusCircle />
            Kompaniyalarni boshqarish
          </Button>
        }
      />

      {query.isError ? (
        <ErrorState error={query.error} className="mt-6" onRetry={() => void query.refetch()} />
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {query.isLoading ? (
              Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)
            ) : (
              <>
                <StatCard label="Jami kompaniyalar" icon={Building2} tone="primary" value={formatNumber(companies.length)} />
                <StatCard label="Faol" icon={Building2} tone="success" value={formatNumber(activeCount)} />
                <StatCard label="Faolsizlantirilgan" icon={Building2} tone="warning" value={formatNumber(suspendedCount)} />
              </>
            )}
          </div>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>So'nggi qo'shilgan kompaniyalar</CardTitle>
              <CardDescription>Oxirgi onboarding faoliyati</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {query.isLoading ? (
                <Skeleton className="m-6 h-48" />
              ) : recent.length === 0 ? (
                <EmptyState
                  compact
                  title="Hozircha kompaniyalar yo'q"
                  action={<Button size="sm" onClick={() => navigate("/companies")}>Yangi kompaniya</Button>}
                />
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead>Nomi</TableHead>
                        <TableHead>Identifikator</TableHead>
                        <TableHead>Yaratilgan</TableHead>
                        <TableHead>Holati</TableHead>
                        <TableHead className="text-right" />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {recent.map((company) => (
                        <TableRow key={company.id}>
                          <TableCell className="font-medium">{company.name}</TableCell>
                          <TableCell className="text-muted-foreground">{company.slug}</TableCell>
                          <TableCell className="text-muted-foreground">{formatDate(company.created_at)}</TableCell>
                          <TableCell>
                            <Badge variant={company.status === "active" ? "success" : "secondary"} dot>
                              {company.status === "active" ? "Faol" : "Faolsizlantirilgan"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={company.status !== "active"}
                              loading={enteringId === company.id}
                              onClick={() => void onEnter(company.id)}
                            >
                              <LogIn className="size-3.5" />
                              Kirish
                            </Button>
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

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

import { cn } from "@/lib/utils";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { reportService } from "@/services/report";
import { storeService } from "@/services/store";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

const CURRENCY = "UZS";

type ReportTab = "sales" | "inventory" | "debts" | "expenses";

const tabs: { id: ReportTab; label: string }[] = [
  { id: "sales", label: "Savdo" },
  { id: "inventory", label: "Ombor" },
  { id: "debts", label: "Qarzlar" },
  { id: "expenses", label: "Xarajatlar" },
];

const paymentStatusLabels: Record<string, string> = {
  paid: "To'liq to'langan",
  partial: "Qisman to'langan",
  unpaid: "To'lanmagan",
};

const debtStatusLabels: Record<string, string> = {
  active: "Faol",
  overdue: "Muddati o'tgan",
};

const expenseTypeLabels: Record<string, string> = {
  fuel: "Yoqilg'i",
  driver: "Haydovchi",
  loader: "Yuk tashuvchi",
  other: "Boshqa",
};

export default function ReportsPage() {
  const { user } = useAuth();
  const isCeo = user?.role === "ceo";
  const [tab, setTab] = React.useState<ReportTab>("sales");
  const [storeId, setStoreId] = React.useState("");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");

  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });
  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
  );

  const storeFilter = storeId ? { store_id: Number(storeId) } : {};

  return (
    <ContentContainer>
      <PageHeader title="Hisobotlar" description="Savdo, ombor, qarz va xarajatlar bo'yicha umumiy ko'rinish." />

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <div className="inline-flex rounded-lg border bg-muted/40 p-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                tab === t.id ? "bg-card text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          {tab === "sales" ? (
            <>
              <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-40" />
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-40" />
            </>
          ) : null}
          {isCeo ? (
            <Select
              options={storeOptions}
              placeholder="Barcha do'konlar"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              className="w-44"
            />
          ) : null}
        </div>
      </div>

      <div className="mt-6">
        {tab === "sales" ? (
          <SalesReportView params={{ ...storeFilter, ...(dateFrom ? { date_from: dateFrom } : {}), ...(dateTo ? { date_to: dateTo } : {}) }} />
        ) : tab === "inventory" ? (
          <InventoryReportView params={storeFilter} />
        ) : tab === "debts" ? (
          <DebtReportView params={storeFilter} />
        ) : (
          <ExpenseReportView params={storeFilter} />
        )}
      </div>
    </ContentContainer>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-tight">{value}</div>
      </CardContent>
    </Card>
  );
}

function SalesReportView({ params }: { params: { store_id?: number; date_from?: string; date_to?: string } }) {
  const query = useQuery({ queryKey: ["reports", "sales", params], queryFn: () => reportService.sales(params) });

  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  if (query.isLoading || !query.data) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  const report = query.data;
  const chartData = report.by_day.map((p) => ({ label: p.label, value: Number(p.value) }));

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard label="Jami daromad" value={formatCurrency(report.total_revenue, CURRENCY)} />
        <StatCard label="Savdolar soni" value={formatNumber(report.total_count)} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Kunlik savdo</CardTitle>
          <CardDescription>Tanlangan davr bo'yicha</CardDescription>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <EmptyState compact title="Ma'lumot yo'q" />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ left: -16, right: 8, top: 8 }}>
                  <defs>
                    <linearGradient id="fillReports" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} className="text-xs" stroke="hsl(var(--muted-foreground))" />
                  <YAxis tickLine={false} axisLine={false} className="text-xs" stroke="hsl(var(--muted-foreground))" />
                  <RechartsTooltip
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "0.5rem",
                      fontSize: "0.8125rem",
                      color: "hsl(var(--popover-foreground))",
                    }}
                    formatter={(value: number) => formatCurrency(value, CURRENCY)}
                  />
                  <Area type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#fillReports)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>To'lov holati bo'yicha</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {report.by_payment_status.length === 0 ? (
            <EmptyState compact title="Ma'lumot yo'q" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Holati</TableHead>
                  <TableHead className="text-right">Soni</TableHead>
                  <TableHead className="text-right">Daromad</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.by_payment_status.map((row) => (
                  <TableRow key={row.status}>
                    <TableCell>{paymentStatusLabels[row.status] ?? row.status}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatNumber(row.count)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatCurrency(row.revenue, CURRENCY)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function InventoryReportView({ params }: { params: { store_id?: number } }) {
  const query = useQuery({ queryKey: ["reports", "inventory", params], queryFn: () => reportService.inventory(params) });

  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  if (query.isLoading || !query.data) return <Skeleton className="h-72 w-full" />;

  const report = query.data;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard label="Mahsulotlar soni" value={formatNumber(report.count)} />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Qoldiqlar</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {report.rows.length === 0 ? (
            <EmptyState compact title="Ma'lumot yo'q" />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Mahsulot</TableHead>
                    <TableHead>SKU</TableHead>
                    <TableHead className="text-right">Miqdor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.rows.map((row) => (
                    <TableRow key={row.product_id}>
                      <TableCell className="font-medium">{row.name}</TableCell>
                      <TableCell className="text-muted-foreground">{row.sku}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatNumber(row.quantity)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function DebtReportView({ params }: { params: { store_id?: number } }) {
  const query = useQuery({ queryKey: ["reports", "debts", params], queryFn: () => reportService.debts(params) });

  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  if (query.isLoading || !query.data) return <Skeleton className="h-72 w-full" />;

  const report = query.data;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard label="Jami ochiq qarz" value={formatCurrency(report.total_remaining, CURRENCY)} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Holati bo'yicha</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {report.by_status.length === 0 ? (
            <EmptyState compact title="Ma'lumot yo'q" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Holati</TableHead>
                  <TableHead className="text-right">Soni</TableHead>
                  <TableHead className="text-right">Qoldiq</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.by_status.map((row) => (
                  <TableRow key={row.status}>
                    <TableCell>{debtStatusLabels[row.status] ?? row.status}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatNumber(row.count)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatCurrency(row.remaining, CURRENCY)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Eng ko'p qarzdorlar</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {report.by_customer.length === 0 ? (
            <EmptyState compact title="Ma'lumot yo'q" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Mijoz</TableHead>
                  <TableHead className="text-right">Qoldiq</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.by_customer.map((row) => (
                  <TableRow key={row.customer_id}>
                    <TableCell className="font-medium">{row.full_name}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatCurrency(row.remaining, CURRENCY)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ExpenseReportView({ params }: { params: { store_id?: number } }) {
  const query = useQuery({ queryKey: ["reports", "expenses", params], queryFn: () => reportService.expenses(params) });

  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  if (query.isLoading || !query.data) return <Skeleton className="h-72 w-full" />;

  const report = query.data;
  const chartData = report.by_date.map((p) => ({ label: p.label, value: Number(p.value) }));

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard label="Jami xarajat" value={formatCurrency(report.total, CURRENCY)} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Kunlik xarajat</CardTitle>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <EmptyState compact title="Ma'lumot yo'q" />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ left: -16, right: 8, top: 8 }}>
                  <defs>
                    <linearGradient id="fillExpenses" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} className="text-xs" stroke="hsl(var(--muted-foreground))" />
                  <YAxis tickLine={false} axisLine={false} className="text-xs" stroke="hsl(var(--muted-foreground))" />
                  <RechartsTooltip
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "0.5rem",
                      fontSize: "0.8125rem",
                      color: "hsl(var(--popover-foreground))",
                    }}
                    formatter={(value: number) => formatCurrency(value, CURRENCY)}
                  />
                  <Area type="monotone" dataKey="value" stroke="hsl(var(--destructive))" strokeWidth={2} fill="url(#fillExpenses)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Turi bo'yicha</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {report.by_type.length === 0 ? (
            <EmptyState compact title="Ma'lumot yo'q" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Turi</TableHead>
                  <TableHead className="text-right">Soni</TableHead>
                  <TableHead className="text-right">Summasi</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.by_type.map((row) => (
                  <TableRow key={row.expense_type}>
                    <TableCell>{expenseTypeLabels[row.expense_type] ?? row.expense_type}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatNumber(row.count)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatCurrency(row.total, CURRENCY)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

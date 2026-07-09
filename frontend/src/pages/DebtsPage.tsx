import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CalendarClock, CheckCircle2, Clock, Wallet } from "lucide-react";

import { businessTodayISO, formatDate, formatMoney, formatNumber } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { customerService } from "@/services/customer";
import { debtService } from "@/services/debt";
import { reportService } from "@/services/report";
import { storeService } from "@/services/store";
import type { Debt, DebtListParams, DebtStatus } from "@/types/debt";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat-card";
import { Label } from "@/components/ui/label";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { SkeletonCard, TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

const statusOptions = [
  { label: "Faol", value: "active" },
  { label: "Muddati o'tgan", value: "overdue" },
  { label: "To'langan", value: "paid" },
];

// Red = overdue, yellow = due today, green = active/paid. "Due today" isn't
// a stored status (the backend keeps status as active until the day after
// due_date), so it's derived here from due_date instead of the raw status.
function resolveBadge(debt: Debt): { variant: "danger" | "warning" | "success"; label: string } {
  if (debt.status === "overdue") return { variant: "danger", label: "Muddati o'tgan" };
  if (debt.status === "paid") return { variant: "success", label: "To'langan" };
  if (debt.due_date === businessTodayISO()) return { variant: "warning", label: "Bugun muddati" };
  return { variant: "success", label: "Faol" };
}

export default function DebtsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isCeo = user?.role === "ceo";

  // Supports deep-linking from the Dashboard's overdue-debt alert
  // (/debts?status=overdue) — read once as the initial value, not kept in
  // sync afterward, so the in-page filter controls remain the source of
  // truth once the user starts interacting with them.
  const [searchParams] = useSearchParams();

  const [storeId, setStoreId] = React.useState("");
  const [customerId, setCustomerId] = React.useState("");
  const [status, setStatus] = React.useState(() => searchParams.get("status") ?? "");
  const [onlyOpen, setOnlyOpen] = React.useState(true);
  const [page, setPage] = React.useState(1);

  const params: DebtListParams = {
    ...(storeId ? { store_id: Number(storeId) } : {}),
    ...(customerId ? { customer_id: Number(customerId) } : {}),
    ...(status ? { status: status as DebtStatus } : {}),
    ...(onlyOpen ? { only_open: true } : {}),
    page,
  };

  React.useEffect(() => {
    setPage(1);
  }, [storeId, customerId, status, onlyOpen]);

  const debtsQuery = useQuery({ queryKey: ["debts", params], queryFn: () => debtService.list(params) });
  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });
  const customersQuery = useQuery({ queryKey: ["customers"], queryFn: customerService.list });

  // Debts page is the single source of truth for debt statistics (Dashboard
  // only keeps a compact overdue alert). These follow the store filter but
  // deliberately ignore status/customer/onlyOpen — they always show the
  // full status breakdown, not a subset of it.
  const summaryStoreId = storeId ? Number(storeId) : undefined;
  const debtReportQuery = useQuery({
    queryKey: ["reports", "debts", "summary", summaryStoreId],
    queryFn: () => reportService.debts(summaryStoreId ? { store_id: summaryStoreId } : {}),
  });
  const dueTodayQuery = useQuery({
    queryKey: ["debts", "due-today", summaryStoreId],
    queryFn: () =>
      debtService.list({
        status: "active",
        only_open: true,
        due_before: businessTodayISO(),
        due_after: businessTodayISO(),
        ...(summaryStoreId ? { store_id: summaryStoreId } : {}),
      }),
  });
  const paidCountQuery = useQuery({
    queryKey: ["debts", "paid-count", summaryStoreId],
    queryFn: () => debtService.list({ status: "paid", ...(summaryStoreId ? { store_id: summaryStoreId } : {}) }),
  });

  const activeBucket = debtReportQuery.data?.by_status.find((b) => b.status === "active");
  const overdueBucket = debtReportQuery.data?.by_status.find((b) => b.status === "overdue");
  const totalDebt = debtReportQuery.data?.total_remaining ?? "0";
  const activeCount = activeBucket?.count ?? 0;
  const overdueCount = overdueBucket?.count ?? 0;
  const overdueTotal = overdueBucket?.remaining ?? "0";
  const dueTodayCount = dueTodayQuery.data?.meta.total ?? 0;
  const paidCount = paidCountQuery.data?.meta.total ?? 0;
  const summaryLoading = debtReportQuery.isLoading || dueTodayQuery.isLoading || paidCountQuery.isLoading;

  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
  );
  const customerOptions = React.useMemo(
    () => (customersQuery.data ?? []).map((c) => ({ label: c.full_name, value: String(c.id) })),
    [customersQuery.data]
  );

  const items = debtsQuery.data?.items ?? [];

  return (
    <ContentContainer>
      <PageHeader title="Qarzlar" description="Mijozlarning ochiq va yopilgan qarzlari." />

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {summaryLoading ? (
          Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard label="Jami qarz" icon={Wallet} tone="primary" value={formatMoney(totalDebt)} />
            <StatCard
              label="Muddati o'tgan"
              icon={AlertTriangle}
              tone="destructive"
              value={formatNumber(overdueCount)}
              sub={formatMoney(overdueTotal)}
            />
            <StatCard label="Bugun muddati" icon={CalendarClock} tone="warning" value={formatNumber(dueTodayCount)} />
            <StatCard label="Faol qarzlar" icon={Clock} tone="success" value={formatNumber(activeCount)} />
            <StatCard label="To'langan" icon={CheckCircle2} tone="success" value={formatNumber(paidCount)} />
          </>
        )}
      </div>

      <div className="mt-6 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Select
            options={customerOptions}
            placeholder="Barcha mijozlar"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            className="w-52"
          />
          <Select
            options={statusOptions}
            placeholder="Barcha holatlar"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-48"
          />
          {isCeo ? (
            <Select
              options={storeOptions}
              placeholder="Barcha do'konlar"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              className="w-44"
            />
          ) : null}
          <div className="flex items-center gap-2 rounded-lg border border-input bg-card px-3 py-2 shadow-xs">
            <Switch id="debts-only-open" checked={onlyOpen} onCheckedChange={setOnlyOpen} />
            <Label htmlFor="debts-only-open" className="cursor-pointer text-sm font-normal">
              Faqat qoldig'i borlar
            </Label>
          </div>
        </div>

        <TableCard>
          {debtsQuery.isError ? (
            <ErrorState error={debtsQuery.error} onRetry={() => void debtsQuery.refetch()} />
          ) : debtsQuery.isLoading ? (
            <TableSkeleton />
          ) : items.length === 0 ? (
            <EmptyState title="Hozircha qarzlar yo'q" description="Bu bo'limda mijozlarning qarzlari ko'rsatiladi." />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Mijoz</TableHead>
                    <TableHead>Boshlanish sanasi</TableHead>
                    <TableHead>Muddati</TableHead>
                    <TableHead>Holati</TableHead>
                    <TableHead className="text-right">Summasi</TableHead>
                    <TableHead className="text-right">Qoldiq</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((debt) => (
                    <TableRow key={debt.id} className="cursor-pointer" onClick={() => navigate(`/debts/${debt.id}`)}>
                      <TableCell className="font-medium">{debt.customer?.full_name ?? "—"}</TableCell>
                      <TableCell className="text-muted-foreground">{formatDate(debt.start_date)}</TableCell>
                      <TableCell className="text-muted-foreground">{debt.due_date ? formatDate(debt.due_date) : "—"}</TableCell>
                      <TableCell>
                        {(() => {
                          const badge = resolveBadge(debt);
                          return (
                            <Badge variant={badge.variant} dot>
                              {badge.label}
                            </Badge>
                          );
                        })()}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{formatMoney(debt.amount)}</TableCell>
                      <TableCell className="text-right font-medium tabular-nums">{formatMoney(debt.remaining_amount)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {debtsQuery.data ? <Pagination meta={debtsQuery.data.meta} onPageChange={setPage} /> : null}
        </TableCard>
      </div>
    </ContentContainer>
  );
}

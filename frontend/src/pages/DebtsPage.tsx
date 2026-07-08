import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { formatDate, formatMoney } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { customerService } from "@/services/customer";
import { debtService } from "@/services/debt";
import { storeService } from "@/services/store";
import type { DebtListParams, DebtStatus } from "@/types/debt";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

const statusOptions = [
  { label: "Faol", value: "active" },
  { label: "Muddati o'tgan", value: "overdue" },
  { label: "To'langan", value: "paid" },
];

const statusLabels: Record<DebtStatus, string> = {
  active: "Faol",
  overdue: "Muddati o'tgan",
  paid: "To'langan",
};

const statusVariant: Record<DebtStatus, "warning" | "danger" | "success"> = {
  active: "warning",
  overdue: "danger",
  paid: "success",
};

export default function DebtsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isCeo = user?.role === "ceo";

  const [storeId, setStoreId] = React.useState("");
  const [customerId, setCustomerId] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [onlyOpen, setOnlyOpen] = React.useState(true);

  const params: DebtListParams = {
    ...(storeId ? { store_id: Number(storeId) } : {}),
    ...(customerId ? { customer_id: Number(customerId) } : {}),
    ...(status ? { status: status as DebtStatus } : {}),
    ...(onlyOpen ? { only_open: true } : {}),
  };

  const debtsQuery = useQuery({ queryKey: ["debts", params], queryFn: () => debtService.list(params) });
  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });
  const customersQuery = useQuery({ queryKey: ["customers"], queryFn: customerService.list });

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
          <div className="flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2 shadow-xs">
            <Switch id="debts-only-open" checked={onlyOpen} onCheckedChange={setOnlyOpen} />
            <Label htmlFor="debts-only-open" className="cursor-pointer text-sm font-normal">
              Faqat qoldig'i borlar
            </Label>
          </div>
        </div>

        <div className="overflow-hidden rounded-lg border bg-card shadow-xs">
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
                        <Badge variant={statusVariant[debt.status]} dot>
                          {statusLabels[debt.status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{formatMoney(debt.amount)}</TableCell>
                      <TableCell className="text-right font-medium tabular-nums">{formatMoney(debt.remaining_amount)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>
    </ContentContainer>
  );
}

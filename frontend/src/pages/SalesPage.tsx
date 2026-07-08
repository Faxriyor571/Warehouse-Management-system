import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";

import { formatDate, formatMoney } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { customerService } from "@/services/customer";
import { saleService } from "@/services/sale";
import { storeService } from "@/services/store";
import type { PaymentStatus, SaleListParams } from "@/types/sale";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

const paymentStatusOptions = [
  { label: "To'liq to'langan", value: "paid" },
  { label: "Qisman to'langan", value: "partial" },
  { label: "To'lanmagan", value: "unpaid" },
];

const paymentStatusLabels: Record<PaymentStatus, string> = {
  paid: "To'liq to'langan",
  partial: "Qisman to'langan",
  unpaid: "To'lanmagan",
};

const paymentStatusVariant: Record<PaymentStatus, "success" | "warning" | "danger"> = {
  paid: "success",
  partial: "warning",
  unpaid: "danger",
};

export default function SalesPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  // Only an actual CEO can filter by store — the legacy admin's reads
  // resolve to (None, None) with no store scoping (see Stock In).
  const isCeo = user?.role === "ceo";

  const [search, setSearch] = React.useState("");
  const [storeId, setStoreId] = React.useState("");
  const [customerId, setCustomerId] = React.useState("");
  const [paymentStatus, setPaymentStatus] = React.useState("");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");

  const params: SaleListParams = {
    ...(search ? { search } : {}),
    ...(storeId ? { store_id: Number(storeId) } : {}),
    ...(customerId ? { customer_id: Number(customerId) } : {}),
    ...(paymentStatus ? { payment_status: paymentStatus as PaymentStatus } : {}),
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
  };

  const salesQuery = useQuery({ queryKey: ["sales", params], queryFn: () => saleService.list(params) });
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

  const items = salesQuery.data?.items ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Savdo"
        description="Savdo hujjatlari. Hujjat yaratilganda ombordagi qoldiq avtomatik kamayadi."
        actions={
          <Button onClick={() => navigate("/sales/new")}>
            <Plus />
            Yangi savdo
          </Button>
        }
      />

      <div className="mt-6 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Input
            placeholder="Hujjat raqami bo'yicha qidirish…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-56"
          />
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-40" />
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-40" />
          <Select
            options={customerOptions}
            placeholder="Barcha mijozlar"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            className="w-52"
          />
          <Select
            options={paymentStatusOptions}
            placeholder="Barcha to'lov holatlari"
            value={paymentStatus}
            onChange={(e) => setPaymentStatus(e.target.value)}
            className="w-56"
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
        </div>

        <div className="overflow-hidden rounded-lg border bg-card shadow-xs">
          {salesQuery.isError ? (
            <ErrorState onRetry={() => void salesQuery.refetch()} />
          ) : salesQuery.isLoading ? (
            <TableSkeleton />
          ) : items.length === 0 ? (
            <EmptyState
              title="Hozircha savdo hujjatlari yo'q"
              description="Boshlash uchun birinchi savdo hujjatingizni yarating."
              action={<Button size="sm" onClick={() => navigate("/sales/new")}>Yangi savdo</Button>}
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Hujjat raqami</TableHead>
                    <TableHead>Sana</TableHead>
                    <TableHead>Mijoz</TableHead>
                    <TableHead>To'lov holati</TableHead>
                    <TableHead className="text-right">Jami</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((sale) => (
                    <TableRow key={sale.id} className="cursor-pointer" onClick={() => navigate(`/sales/${sale.id}`)}>
                      <TableCell className="font-medium">{sale.reference}</TableCell>
                      <TableCell className="text-muted-foreground">{formatDate(sale.date)}</TableCell>
                      <TableCell className="text-muted-foreground">{sale.customer?.full_name ?? "—"}</TableCell>
                      <TableCell>
                        <Badge variant={paymentStatusVariant[sale.payment_status]} dot>
                          {paymentStatusLabels[sale.payment_status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{formatMoney(sale.total_amount)}</TableCell>
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

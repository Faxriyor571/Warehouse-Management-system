import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";

import { formatDate, formatMoney } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { stockInService } from "@/services/stock-in";
import { storeService } from "@/services/store";
import { supplierService } from "@/services/supplier";
import type { StockInListParams } from "@/types/stock-in";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

export default function StockInPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  // Only an actual CEO can filter by store — the legacy admin's reads
  // resolve to (None, None) with no store scoping (see StockInNewPage).
  const isCeo = user?.role === "ceo";

  const [search, setSearch] = React.useState("");
  const [storeId, setStoreId] = React.useState("");
  const [supplierId, setSupplierId] = React.useState("");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");

  const params: StockInListParams = {
    ...(search ? { search } : {}),
    ...(storeId ? { store_id: Number(storeId) } : {}),
    ...(supplierId ? { supplier_id: Number(supplierId) } : {}),
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
  };

  const stockInQuery = useQuery({
    queryKey: ["stock-in", params],
    queryFn: () => stockInService.list(params),
  });

  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });
  const suppliersQuery = useQuery({ queryKey: ["suppliers"], queryFn: supplierService.list });

  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
  );
  const supplierOptions = React.useMemo(
    () => (suppliersQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [suppliersQuery.data]
  );

  const items = stockInQuery.data?.items ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Kirim"
        description="Kirim hujjatlari. Hujjat yaratilganda ombordagi qoldiq avtomatik oshadi."
        actions={
          <Button onClick={() => navigate("/stock-in/new")}>
            <Plus />
            Yangi kirim
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
            options={supplierOptions}
            placeholder="Barcha yetkazib beruvchilar"
            value={supplierId}
            onChange={(e) => setSupplierId(e.target.value)}
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

        <div className="overflow-hidden rounded-lg border">
          {stockInQuery.isError ? (
            <ErrorState onRetry={() => void stockInQuery.refetch()} />
          ) : stockInQuery.isLoading ? (
            <div className="space-y-3 p-6">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : items.length === 0 ? (
            <EmptyState title="Hozircha kirim hujjatlari yo'q" description="Boshlash uchun birinchi kirim hujjatingizni yarating." />
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-6 py-2 text-left font-medium">Hujjat raqami</th>
                  <th className="px-6 py-2 text-left font-medium">Sana</th>
                  <th className="px-6 py-2 text-left font-medium">Yetkazib beruvchi</th>
                  <th className="px-6 py-2 text-right font-medium">Qatorlar</th>
                  <th className="px-6 py-2 text-right font-medium">Jami</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {items.map((doc) => (
                  <tr key={doc.id} className="cursor-pointer hover:bg-accent/50" onClick={() => navigate(`/stock-in/${doc.id}`)}>
                    <td className="px-6 py-2.5 font-medium">{doc.reference}</td>
                    <td className="px-6 py-2.5 text-muted-foreground">{formatDate(doc.date)}</td>
                    <td className="px-6 py-2.5 text-muted-foreground">{doc.supplier?.name ?? "—"}</td>
                    <td className="px-6 py-2.5 text-right tabular-nums">{doc.items.length}</td>
                    <td className="px-6 py-2.5 text-right tabular-nums">{formatMoney(doc.total_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </ContentContainer>
  );
}

import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";

import { formatDate, formatMoney } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { stockInService } from "@/services/stock-in";
import { storeService } from "@/services/store";
import type { StockInListParams } from "@/types/stock-in";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input, SearchInput } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { TableSkeleton } from "@/components/ui/skeleton";
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
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [page, setPage] = React.useState(1);

  const params: StockInListParams = {
    ...(search ? { search } : {}),
    ...(storeId ? { store_id: Number(storeId) } : {}),
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
    page,
  };

  React.useEffect(() => {
    setPage(1);
  }, [search, storeId, dateFrom, dateTo]);

  const stockInQuery = useQuery({
    queryKey: ["stock-in", params],
    queryFn: () => stockInService.list(params),
  });

  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });

  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
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
          <SearchInput
            placeholder="Hujjat raqami bo'yicha qidirish…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-56"
          />
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-40" />
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-40" />
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

        <TableCard>
          {stockInQuery.isError ? (
            <ErrorState error={stockInQuery.error} onRetry={() => void stockInQuery.refetch()} />
          ) : stockInQuery.isLoading ? (
            <TableSkeleton />
          ) : items.length === 0 ? (
            <EmptyState
              title="Hozircha kirim hujjatlari yo'q"
              description="Boshlash uchun birinchi kirim hujjatingizni yarating."
              action={<Button size="sm" onClick={() => navigate("/stock-in/new")}>Yangi kirim</Button>}
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Hujjat raqami</TableHead>
                    <TableHead>Sana</TableHead>
                    <TableHead className="text-right">Qatorlar</TableHead>
                    <TableHead className="text-right">Jami</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((doc) => (
                    <TableRow key={doc.id} className="cursor-pointer" onClick={() => navigate(`/stock-in/${doc.id}`)}>
                      <TableCell className="font-medium">{doc.reference}</TableCell>
                      <TableCell className="text-muted-foreground">{formatDate(doc.date)}</TableCell>
                      <TableCell className="text-right tabular-nums">{doc.items.length}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatMoney(doc.total_amount)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {stockInQuery.data ? <Pagination meta={stockInQuery.data.meta} onPageChange={setPage} /> : null}
        </TableCard>
      </div>
    </ContentContainer>
  );
}

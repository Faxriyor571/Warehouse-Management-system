import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";

import { formatDateTime, formatMoney, formatQuantity } from "@/lib/formatters";
import { productService } from "@/services/product";
import { stockInService } from "@/services/stock-in";
import { storeService } from "@/services/store";
import type { Product } from "@/types/product";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/feedback/error-state";

export default function StockInDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const stockInId = Number(id);

  const stockInQuery = useQuery({ queryKey: ["stock-in", stockInId], queryFn: () => stockInService.get(stockInId) });
  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list });
  // Stock-in items embed only ProductBrief (no unit) server-side — cross
  // -reference the product catalog (which does carry unit) by product_id.
  const productsQuery = useQuery({ queryKey: ["products"], queryFn: productService.list });
  const productById = React.useMemo(() => {
    const map = new Map<number, Product>();
    for (const p of productsQuery.data ?? []) map.set(p.id, p);
    return map;
  }, [productsQuery.data]);

  const doc = stockInQuery.data;
  const store = (storesQuery.data ?? []).find((s) => s.id === doc?.store_id);

  return (
    <ContentContainer>
      <PageHeader
        title={doc ? doc.reference : "Kirim"}
        actions={
          <div className="flex gap-2 print:hidden">
            <Button variant="outline" onClick={() => navigate("/stock-in")}>
              Ortga
            </Button>
            <Button variant="outline" disabled={!doc} onClick={() => window.print()}>
              <Printer />
              Chop etish
            </Button>
          </div>
        }
      />

      <div className="mt-6">
        {stockInQuery.isError ? (
          <ErrorState error={stockInQuery.error} onRetry={() => void stockInQuery.refetch()} />
        ) : stockInQuery.isLoading || !doc ? (
          <div className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 rounded-xl border border-border/70 bg-card p-5 shadow-panel sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Sana" value={formatDateTime(doc.date)} />
              <Field label="Do'kon" value={store?.name ?? "—"} />
              <Field label="Yaratgan xodim" value={doc.created_by?.full_name ?? "—"} />
              {doc.note ? (
                <div className="sm:col-span-2 lg:col-span-3">
                  <Field label="Izoh" value={doc.note} />
                </div>
              ) : null}
            </div>

            <TableCard>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead>Mahsulot</TableHead>
                      <TableHead className="text-right">Miqdor</TableHead>
                      <TableHead className="text-right">Narx</TableHead>
                      <TableHead className="text-right">Oraliq summa</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {doc.items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>{item.product ? `${item.product.name} (${item.product.sku})` : `Mahsulot #${item.product_id}`}</TableCell>
                        <TableCell className="text-right tabular-nums whitespace-nowrap">
                          {formatQuantity(item.quantity, productById.get(item.product_id)?.unit)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{formatMoney(item.price)}</TableCell>
                        <TableCell className="text-right tabular-nums">{formatMoney(item.subtotal)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TableCard>

            <div className="flex justify-end">
              <div className="w-full max-w-xs space-y-1 rounded-xl border border-border/70 bg-card p-5 shadow-panel">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Jami</span>
                  <span className="font-medium tabular-nums">{formatMoney(doc.total_amount)}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </ContentContainer>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-sm text-foreground">{value}</p>
    </div>
  );
}

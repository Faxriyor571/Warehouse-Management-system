import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Layers } from "lucide-react";

import { formatDateTime, formatNumber } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { inventoryService } from "@/services/inventory";
import { productService } from "@/services/product";
import { storeService } from "@/services/store";
import type { MovementListParams, MovementType, StoreStockListParams } from "@/types/inventory";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, SearchInput } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { SegmentedTabs } from "@/components/ui/segmented-tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

type InventoryTab = "stock" | "movements";

const tabs: { id: InventoryTab; label: string }[] = [
  { id: "stock", label: "Do'kon zaxirasi" },
  { id: "movements", label: "Harakatlar jurnali" },
];

const movementTypeOptions = [
  { label: "Kirim", value: "stock_in" },
  { label: "Savdo", value: "sale" },
  { label: "Qaytarish", value: "sales_return" },
  { label: "Tuzatish", value: "adjustment" },
];

const movementTypeLabels: Record<MovementType, string> = {
  stock_in: "Kirim",
  sale: "Savdo",
  sales_return: "Qaytarish",
  adjustment: "Tuzatish",
};

const movementTypeVariant: Record<MovementType, "success" | "danger" | "warning" | "secondary"> = {
  stock_in: "success",
  sale: "danger",
  sales_return: "warning",
  adjustment: "secondary",
};

export default function InventoryPage() {
  const { user } = useAuth();
  const isCeo = user?.role === "ceo";
  const [tab, setTab] = React.useState<InventoryTab>("stock");
  const [storeId, setStoreId] = React.useState("");

  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });
  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
  );

  return (
    <ContentContainer>
      <PageHeader title="Ombor" description="Do'kon bo'yicha zaxira va zaxira harakatlari jurnali." />

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <SegmentedTabs value={tab} onChange={setTab} options={tabs} />
        <div className="ml-auto flex flex-wrap items-center gap-2">
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
        {tab === "stock" ? (
          <StoreStockView storeId={storeId ? Number(storeId) : undefined} />
        ) : (
          <MovementsView storeId={storeId ? Number(storeId) : undefined} />
        )}
      </div>
    </ContentContainer>
  );
}

function StoreStockView({ storeId }: { storeId?: number }) {
  const [search, setSearch] = React.useState("");
  const [crossStoreProduct, setCrossStoreProduct] = React.useState<{ id: number; name: string } | null>(null);

  const params: StoreStockListParams = { ...(storeId ? { store_id: storeId } : {}), ...(search ? { search } : {}) };
  const query = useQuery({ queryKey: ["inventory", "store-stock", params], queryFn: () => inventoryService.storeStock(params) });
  const crossStoreQuery = useQuery({
    queryKey: ["inventory", "cross-store", crossStoreProduct?.id],
    queryFn: () => inventoryService.crossStore(crossStoreProduct!.id),
    enabled: crossStoreProduct !== null,
  });

  const items = query.data?.items ?? [];

  return (
    <div className="space-y-4">
      <SearchInput
        placeholder="Mahsulot nomi yoki SKU bo'yicha qidirish…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-72"
      />

      <TableCard>
        {query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.isLoading ? (
          <TableSkeleton />
        ) : items.length === 0 ? (
          <EmptyState title="Zaxira ma'lumotlari yo'q" description="Bu bo'limda do'kondagi mahsulot qoldiqlari ko'rsatiladi." />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Mahsulot</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead className="text-right">Miqdor</TableHead>
                  <TableHead className="text-right" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((row) => (
                  <TableRow key={row.product_id}>
                    <TableCell className="font-medium">{row.product_name}</TableCell>
                    <TableCell className="text-muted-foreground">{row.sku}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatNumber(row.quantity)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => setCrossStoreProduct({ id: row.product_id, name: row.product_name })}
                        aria-label="Barcha do'konlar bo'yicha"
                      >
                        <Layers className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </TableCard>

      <Modal
        open={crossStoreProduct !== null}
        onOpenChange={(open) => !open && setCrossStoreProduct(null)}
        title={crossStoreProduct?.name}
        description="Mahsulotning barcha do'konlardagi qoldig'i."
      >
        {crossStoreQuery.isLoading ? (
          <TableSkeleton rows={2} />
        ) : (crossStoreQuery.data ?? []).length === 0 ? (
          <EmptyState compact title="Ma'lumot yo'q" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Do'kon</TableHead>
                <TableHead className="text-right">Miqdor</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(crossStoreQuery.data ?? []).map((row) => (
                <TableRow key={row.store_id}>
                  <TableCell className="font-medium">{row.store_name}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatNumber(row.quantity)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Modal>
    </div>
  );
}

function MovementsView({ storeId }: { storeId?: number }) {
  const [productId, setProductId] = React.useState("");
  const [movementType, setMovementType] = React.useState("");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");

  const productsQuery = useQuery({ queryKey: ["products"], queryFn: productService.list });
  const productOptions = React.useMemo(
    () => (productsQuery.data ?? []).map((p) => ({ label: `${p.name} (${p.sku})`, value: String(p.id) })),
    [productsQuery.data]
  );

  const params: MovementListParams = {
    ...(storeId ? { store_id: storeId } : {}),
    ...(productId ? { product_id: Number(productId) } : {}),
    ...(movementType ? { movement_type: movementType as MovementType } : {}),
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
  };
  const query = useQuery({ queryKey: ["inventory", "movements", params], queryFn: () => inventoryService.movements(params) });

  const items = query.data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Select
          options={productOptions}
          placeholder="Barcha mahsulotlar"
          value={productId}
          onChange={(e) => setProductId(e.target.value)}
          className="w-56"
        />
        <Select
          options={movementTypeOptions}
          placeholder="Barcha turlar"
          value={movementType}
          onChange={(e) => setMovementType(e.target.value)}
          className="w-44"
        />
        <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-40" />
        <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-40" />
      </div>

      <TableCard>
        {query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.isLoading ? (
          <TableSkeleton />
        ) : items.length === 0 ? (
          <EmptyState title="Harakatlar yo'q" description="Bu bo'limda zaxira harakatlari jurnali ko'rsatiladi." />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Sana</TableHead>
                  <TableHead>Turi</TableHead>
                  <TableHead className="text-right">O'zgarish</TableHead>
                  <TableHead>Hujjat</TableHead>
                  <TableHead>Xodim</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((movement) => (
                  <TableRow key={movement.id}>
                    <TableCell className="text-muted-foreground">{formatDateTime(movement.created_at)}</TableCell>
                    <TableCell>
                      <Badge variant={movementTypeVariant[movement.movement_type]} dot>
                        {movementTypeLabels[movement.movement_type]}
                      </Badge>
                    </TableCell>
                    <TableCell
                      className={`text-right tabular-nums font-medium ${Number(movement.quantity_delta) < 0 ? "text-destructive" : "text-success"}`}
                    >
                      {Number(movement.quantity_delta) > 0 ? "+" : ""}
                      {formatNumber(movement.quantity_delta)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {movement.reference_type}
                      {movement.reference_id ? ` #${movement.reference_id}` : ""}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{movement.created_by ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </TableCard>
    </div>
  );
}

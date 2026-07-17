import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Boxes, DollarSign, Pencil, Power, ShoppingCart, Wallet } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { businessTodayISO, formatDate, formatMoney, formatUnitLabel } from "@/lib/formatters";
import { toastMutationError } from "@/lib/mutation";
import { useAuth } from "@/providers/auth-provider";
import { inventoryService } from "@/services/inventory";
import { productService } from "@/services/product";
import { reportService } from "@/services/report";
import { saleService } from "@/services/sale";
import { storeService } from "@/services/store";
import type { Product } from "@/types/product";
import type { PaymentStatus } from "@/types/sale";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { StatCard } from "@/components/ui/stat-card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { SkeletonCard, TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";

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

const storeFormSchema = z.object({
  name: z.string().min(2, "Nomi kamida 2 belgidan iborat bo'lishi kerak"),
  address: z.string().optional(),
});
type StoreFormValues = z.infer<typeof storeFormSchema>;

export default function StoreDetailPage() {
  const { id } = useParams<{ id: string }>();
  const storeId = Number(id);
  const navigate = useNavigate();
  const { user } = useAuth();
  const isCeo = user?.role === "ceo";
  const queryClient = useQueryClient();
  const [editing, setEditing] = React.useState(false);
  const [deactivating, setDeactivating] = React.useState(false);

  const storeQuery = useQuery({
    queryKey: ["stores", storeId],
    queryFn: () => storeService.get(storeId),
    enabled: Number.isFinite(storeId),
  });
  const stockQuery = useQuery({
    queryKey: ["inventory", "store-stock", storeId],
    queryFn: () => inventoryService.storeStock({ store_id: storeId }),
  });
  const productsQuery = useQuery({ queryKey: ["products"], queryFn: productService.list });
  const salesQuery = useQuery({
    queryKey: ["sales", { store_id: storeId }],
    queryFn: () => saleService.list({ store_id: storeId, page: 1 }),
  });

  // Reuses the existing sales report (already store + date-range scoped)
  // rather than a new endpoint — one call for today, one for the month.
  const today = businessTodayISO();
  const monthStart = `${today.slice(0, 7)}-01`;
  const todaySalesQuery = useQuery({
    queryKey: ["reports", "sales", "store-detail-today", storeId],
    queryFn: () => reportService.sales({ store_id: storeId, date_from: today, date_to: today }),
  });
  const monthSalesQuery = useQuery({
    queryKey: ["reports", "sales", "store-detail-month", storeId],
    queryFn: () => reportService.sales({ store_id: storeId, date_from: monthStart, date_to: today }),
  });

  const form = useForm<StoreFormValues>({
    resolver: zodResolver(storeFormSchema),
    defaultValues: { name: "", address: "" },
  });

  React.useEffect(() => {
    if (storeQuery.data) form.reset({ name: storeQuery.data.name, address: storeQuery.data.address ?? "" });
  }, [storeQuery.data, form]);

  const updateMutation = useMutation({
    mutationFn: (values: StoreFormValues) => storeService.update(storeId, values),
    onSuccess: () => {
      toast.success("Do'kon yangilandi.");
      setEditing(false);
      void queryClient.invalidateQueries({ queryKey: ["stores"] });
    },
    onError: toastMutationError,
  });

  const deactivateMutation = useMutation({
    mutationFn: () => storeService.deactivate(storeId),
    onSuccess: () => {
      toast.success("Do'kon faolsizlantirildi.");
      setDeactivating(false);
      void queryClient.invalidateQueries({ queryKey: ["stores"] });
      void queryClient.invalidateQueries({ queryKey: ["stores", storeId] });
    },
    onError: toastMutationError,
  });

  // Inventory value isn't a field the backend returns anywhere — computed
  // here from each row's quantity × the product's current sale price.
  const productById = React.useMemo(() => {
    const map = new Map<number, Product>();
    for (const p of productsQuery.data ?? []) map.set(p.id, p);
    return map;
  }, [productsQuery.data]);

  const stockRows = stockQuery.data?.items ?? [];
  const inventoryValue = stockRows.reduce((sum, row) => {
    const price = Number(productById.get(row.product_id)?.sale_price ?? 0);
    return sum + Number(row.quantity) * price;
  }, 0);
  const recentSales = salesQuery.data?.items ?? [];

  if (storeQuery.isError) {
    return (
      <ContentContainer>
        <ErrorState error={storeQuery.error} onRetry={() => void storeQuery.refetch()} />
      </ContentContainer>
    );
  }

  return (
    <ContentContainer>
      <PageHeader
        title={storeQuery.data?.name ?? "Do'kon"}
        description={
          storeQuery.data ? (
            <Badge variant={storeQuery.data.is_active ? "success" : "secondary"} dot>
              {storeQuery.data.is_active ? "Faol" : "Nofaol"}
            </Badge>
          ) : undefined
        }
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate("/stores")}>
              Ortga
            </Button>
            {isCeo ? (
              <>
                <Button variant="outline" onClick={() => setEditing(true)}>
                  <Pencil />
                  Tahrirlash
                </Button>
                <Button
                  variant="outline"
                  disabled={!storeQuery.data?.is_active}
                  onClick={() => setDeactivating(true)}
                >
                  <Power />
                  Faolsizlantirish
                </Button>
              </>
            ) : null}
          </div>
        }
      />

      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stockQuery.isLoading || todaySalesQuery.isLoading || monthSalesQuery.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard label="Ombor qiymati" icon={Wallet} tone="primary" value={formatMoney(inventoryValue)} />
            <StatCard label="Mahsulotlar soni" icon={Boxes} tone="success" value={String(stockRows.length)} />
            <StatCard
              label="Bugungi savdolar"
              icon={ShoppingCart}
              tone="warning"
              value={formatMoney(todaySalesQuery.data?.total_revenue ?? "0")}
            />
            <StatCard
              label="Oylik savdolar"
              icon={DollarSign}
              tone="success"
              value={formatMoney(monthSalesQuery.data?.total_revenue ?? "0")}
            />
          </>
        )}
      </div>

      <div className="mt-6 space-y-3">
        <h2 className="text-sm font-medium text-foreground">Ombordagi qoldiq</h2>
        <TableCard>
          {stockQuery.isError ? (
            <ErrorState error={stockQuery.error} onRetry={() => void stockQuery.refetch()} />
          ) : stockQuery.isLoading ? (
            <TableSkeleton />
          ) : stockRows.length === 0 ? (
            <EmptyState compact title="Ombor bo'sh" description="Bu do'konda hali mahsulot qoldig'i yo'q." />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Mahsulot</TableHead>
                    <TableHead className="text-right">Miqdor</TableHead>
                    <TableHead>Birlik</TableHead>
                    <TableHead className="text-right">Qiymat</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stockRows.map((row) => {
                    const product = productById.get(row.product_id);
                    const value = Number(row.quantity) * Number(product?.sale_price ?? 0);
                    return (
                      <TableRow key={row.product_id}>
                        <TableCell className="font-medium">{row.product_name}</TableCell>
                        <TableCell className="text-right tabular-nums">{row.quantity}</TableCell>
                        <TableCell className="text-muted-foreground">{formatUnitLabel(product?.unit)}</TableCell>
                        <TableCell className="text-right tabular-nums">{formatMoney(value)}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </TableCard>
      </div>

      <div className="mt-6 space-y-3">
        <h2 className="text-sm font-medium text-foreground">So'nggi savdolar</h2>
        <TableCard>
          {salesQuery.isError ? (
            <ErrorState error={salesQuery.error} onRetry={() => void salesQuery.refetch()} />
          ) : salesQuery.isLoading ? (
            <TableSkeleton />
          ) : recentSales.length === 0 ? (
            <EmptyState compact title="Hozircha savdolar yo'q" description="Bu do'konda hali savdo qayd etilmagan." />
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
                  {recentSales.map((sale) => (
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
        </TableCard>
      </div>

      <Modal
        open={editing}
        onOpenChange={setEditing}
        title="Do'konni tahrirlash"
        footer={
          <>
            <Button variant="outline" onClick={() => setEditing(false)}>
              Bekor qilish
            </Button>
            <Button onClick={form.handleSubmit((v) => updateMutation.mutate(v))} loading={updateMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={form.handleSubmit((v) => updateMutation.mutate(v))}>
          <FormField htmlFor="store-edit-name" label="Nomi" required error={form.formState.errors.name?.message}>
            <Input id="store-edit-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
          </FormField>
          <FormField htmlFor="store-edit-address" label="Manzil">
            <Input id="store-edit-address" {...form.register("address")} />
          </FormField>
        </form>
      </Modal>

      <ConfirmDialog
        open={deactivating}
        onOpenChange={setDeactivating}
        title={`${storeQuery.data?.name} faolsizlantirilsinmi?`}
        description="Do'kon endi yangi amaliyotlar uchun ishlatib bo'lmaydi."
        confirmLabel="Faolsizlantirish"
        variant="destructive"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateMutation.mutate()}
      />
    </ContentContainer>
  );
}

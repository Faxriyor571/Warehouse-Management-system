import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Printer, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { toastMutationError } from "@/lib/mutation";
import { formatDateTime, formatMoney, formatNumber } from "@/lib/formatters";
import { saleService } from "@/services/sale";
import { storeService } from "@/services/store";
import type { PaymentStatus, SalesReturnFormValues } from "@/types/sale";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { Skeleton } from "@/components/ui/skeleton";
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

export default function SalesDetailPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id } = useParams<{ id: string }>();
  const saleId = Number(id);
  const [returnModalOpen, setReturnModalOpen] = React.useState(false);
  const [returnQuantities, setReturnQuantities] = React.useState<Record<number, string>>({});
  const [returnReason, setReturnReason] = React.useState("");

  const saleQuery = useQuery({ queryKey: ["sales", saleId], queryFn: () => saleService.get(saleId) });
  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list });
  const returnsQuery = useQuery({ queryKey: ["sales", saleId, "returns"], queryFn: () => saleService.listReturns(saleId) });

  const sale = saleQuery.data;
  const store = (storesQuery.data ?? []).find((s) => s.id === sale?.store_id);

  const returnMutation = useMutation({
    mutationFn: (values: SalesReturnFormValues) => saleService.createReturn(saleId, values),
    onSuccess: () => {
      toast.success("Qaytarish muvaffaqiyatli qayd etildi.");
      setReturnModalOpen(false);
      setReturnQuantities({});
      setReturnReason("");
      void queryClient.invalidateQueries({ queryKey: ["sales", saleId] });
      void queryClient.invalidateQueries({ queryKey: ["sales", saleId, "returns"] });
    },
    onError: toastMutationError,
  });

  const openReturnModal = () => {
    setReturnQuantities({});
    setReturnReason("");
    setReturnModalOpen(true);
  };

  const onSubmitReturn = () => {
    const items = Object.entries(returnQuantities)
      .map(([stockOutItemId, qty]) => ({ stock_out_item_id: Number(stockOutItemId), quantity: Number(qty) }))
      .filter((item) => item.quantity > 0);
    if (items.length === 0) {
      toast.error("Kamida bitta qatorga miqdor kiriting.");
      return;
    }
    returnMutation.mutate({ reason: returnReason || undefined, items });
  };

  return (
    <ContentContainer>
      <PageHeader
        title={sale ? sale.reference : "Savdo"}
        actions={
          <div className="flex gap-2 print:hidden">
            <Button variant="outline" onClick={() => navigate("/sales")}>
              Ortga
            </Button>
            <Button variant="outline" disabled={!sale} onClick={openReturnModal}>
              <RotateCcw />
              Qaytarish
            </Button>
            <Button variant="outline" disabled={!sale} onClick={() => window.print()}>
              <Printer />
              Chop etish
            </Button>
          </div>
        }
      />

      <div className="mt-6">
        {saleQuery.isError ? (
          <ErrorState error={saleQuery.error} onRetry={() => void saleQuery.refetch()} />
        ) : saleQuery.isLoading || !sale ? (
          <div className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 rounded-xl border border-border/70 bg-card p-5 shadow-panel sm:grid-cols-2 lg:grid-cols-4">
              <Field label="Sana" value={formatDateTime(sale.date)} />
              <Field label="Do'kon" value={store?.name ?? "—"} />
              <Field label="Mijoz" value={sale.customer?.full_name ?? "—"} />
              <Field
                label="To'lov holati"
                value={
                  <Badge variant={paymentStatusVariant[sale.payment_status]} dot>
                    {paymentStatusLabels[sale.payment_status]}
                  </Badge>
                }
              />
              {sale.note ? (
                <div className="sm:col-span-2 lg:col-span-4">
                  <Field label="Izoh" value={sale.note} />
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
                      <TableHead className="text-right">Chegirma</TableHead>
                      <TableHead className="text-right">Oraliq summa</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sale.items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>{item.product ? `${item.product.name} (${item.product.sku})` : `Mahsulot #${item.product_id}`}</TableCell>
                        <TableCell className="text-right tabular-nums">{formatNumber(item.quantity)}</TableCell>
                        <TableCell className="text-right tabular-nums">{formatMoney(item.price)}</TableCell>
                        <TableCell className="text-right tabular-nums">{formatMoney(item.discount)}</TableCell>
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
                  <span className="text-muted-foreground">Oraliq summa</span>
                  <span className="tabular-nums">{formatMoney(sale.subtotal)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Chegirma</span>
                  <span className="tabular-nums">{formatMoney(sale.discount)}</span>
                </div>
                <div className="flex justify-between text-sm font-medium">
                  <span>Jami</span>
                  <span className="tabular-nums">{formatMoney(sale.total_amount)}</span>
                </div>
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>To'langan</span>
                  <span className="tabular-nums">{formatMoney(sale.paid_amount)}</span>
                </div>
              </div>
            </div>

            {sale.payments.length > 0 ? (
              <div>
                <h2 className="mb-3 text-sm font-medium text-foreground">To'lovlar</h2>
                <TableCard>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="hover:bg-transparent">
                          <TableHead>To'lov turi</TableHead>
                          <TableHead>Sana</TableHead>
                          <TableHead>Izoh</TableHead>
                          <TableHead className="text-right">Summasi</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sale.payments.map((payment) => (
                          <TableRow key={payment.id}>
                            <TableCell>{payment.payment_method?.name ?? "—"}</TableCell>
                            <TableCell className="text-muted-foreground">{formatDateTime(payment.date)}</TableCell>
                            <TableCell className="text-muted-foreground">{payment.note ?? "—"}</TableCell>
                            <TableCell className="text-right tabular-nums">{formatMoney(payment.amount)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </TableCard>
              </div>
            ) : null}

            {(returnsQuery.data ?? []).length > 0 ? (
              <div>
                <h2 className="mb-3 text-sm font-medium text-foreground">Qaytarishlar</h2>
                <TableCard>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="hover:bg-transparent">
                          <TableHead>Hujjat raqami</TableHead>
                          <TableHead>Sana</TableHead>
                          <TableHead>Sabab</TableHead>
                          <TableHead className="text-right">Summasi</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(returnsQuery.data ?? []).map((ret) => (
                          <TableRow key={ret.id}>
                            <TableCell className="font-medium">{ret.reference}</TableCell>
                            <TableCell className="text-muted-foreground">{formatDateTime(ret.date)}</TableCell>
                            <TableCell className="text-muted-foreground">{ret.reason ?? "—"}</TableCell>
                            <TableCell className="text-right tabular-nums">{formatMoney(ret.total_amount)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </TableCard>
              </div>
            ) : null}
          </div>
        )}
      </div>

      <Modal
        open={returnModalOpen}
        onOpenChange={setReturnModalOpen}
        title="Savdoni qaytarish"
        description="Qaytariladigan qatorlar uchun miqdorni kiriting."
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setReturnModalOpen(false)}>
              Bekor qilish
            </Button>
            <Button onClick={onSubmitReturn} loading={returnMutation.isPending}>
              Qaytarish
            </Button>
          </>
        }
      >
        {sale ? (
          <div className="space-y-4">
            <div className="space-y-3">
              {sale.items.map((item) => (
                <div key={item.id} className="grid grid-cols-[2fr_1fr] items-end gap-3 rounded-lg border p-3">
                  <div className="space-y-1">
                    <p className="text-sm font-medium">{item.product ? `${item.product.name} (${item.product.sku})` : `Mahsulot #${item.product_id}`}</p>
                    <p className="text-xs text-muted-foreground">Sotilgan: {formatNumber(item.quantity)}</p>
                  </div>
                  <FormField htmlFor={`return-qty-${item.id}`} label="Qaytarish miqdori">
                    <Input
                      id={`return-qty-${item.id}`}
                      type="number"
                      step="0.001"
                      min={0}
                      max={Number(item.quantity)}
                      value={returnQuantities[item.id] ?? ""}
                      onChange={(e) => setReturnQuantities((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    />
                  </FormField>
                </div>
              ))}
            </div>
            <FormField htmlFor="return-reason" label="Sabab">
              <Input id="return-reason" value={returnReason} onChange={(e) => setReturnReason(e.target.value)} />
            </FormField>
          </div>
        ) : null}
      </Modal>
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

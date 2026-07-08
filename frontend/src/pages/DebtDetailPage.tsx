import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { CalendarClock, Plus } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { formatDate, formatDateTime, formatMoney } from "@/lib/formatters";
import { debtService } from "@/services/debt";
import { paymentMethodService } from "@/services/payment-method";
import type { DebtStatus } from "@/types/debt";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";

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

const paymentFormSchema = z.object({
  amount: z.coerce.number({ invalid_type_error: "Summasi raqam bo'lishi kerak" }).positive("0 dan katta bo'lishi kerak"),
  payment_method_id: z.string().min(1, "To'lov turini tanlash shart"),
  note: z.string().optional(),
});
type PaymentFormValues = z.infer<typeof paymentFormSchema>;

const dueDateFormSchema = z.object({
  due_date: z.string().optional(),
});
type DueDateFormValues = z.infer<typeof dueDateFormSchema>;

export default function DebtDetailPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id } = useParams<{ id: string }>();
  const debtId = Number(id);
  const [paymentModalOpen, setPaymentModalOpen] = React.useState(false);
  const [dueDateModalOpen, setDueDateModalOpen] = React.useState(false);

  const debtQuery = useQuery({ queryKey: ["debts", debtId], queryFn: () => debtService.get(debtId) });
  const paymentMethodsQuery = useQuery({ queryKey: ["payment-methods"], queryFn: paymentMethodService.list });

  const debt = debtQuery.data;

  const paymentMethodOptions = React.useMemo(
    () => (paymentMethodsQuery.data ?? []).filter((m) => m.is_active).map((m) => ({ label: m.name, value: String(m.id) })),
    [paymentMethodsQuery.data]
  );

  const paymentForm = useForm<PaymentFormValues>({
    resolver: zodResolver(paymentFormSchema),
    defaultValues: { amount: 0, payment_method_id: "", note: "" },
  });

  const dueDateForm = useForm<DueDateFormValues>({
    resolver: zodResolver(dueDateFormSchema),
    defaultValues: { due_date: "" },
  });

  React.useEffect(() => {
    if (dueDateModalOpen && debt) {
      dueDateForm.reset({ due_date: debt.due_date ?? "" });
    }
  }, [dueDateModalOpen, debt, dueDateForm]);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["debts", debtId] });
    void queryClient.invalidateQueries({ queryKey: ["debts"] });
  };

  const paymentMutation = useMutation({
    mutationFn: (values: PaymentFormValues) => debtService.addPayment(debtId, values),
    onSuccess: () => {
      toast.success("To'lov qayd etildi.");
      setPaymentModalOpen(false);
      paymentForm.reset({ amount: 0, payment_method_id: "", note: "" });
      invalidate();
    },
    onError: toastMutationError,
  });

  const dueDateMutation = useMutation({
    mutationFn: (values: DueDateFormValues) => debtService.updateDueDate(debtId, values),
    onSuccess: () => {
      toast.success("Qarz muddati yangilandi.");
      setDueDateModalOpen(false);
      invalidate();
    },
    onError: toastMutationError,
  });

  return (
    <ContentContainer>
      <PageHeader
        title={debt ? `${debt.customer?.full_name ?? "Qarz"}` : "Qarz"}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate("/debts")}>
              Ortga
            </Button>
            <Button variant="outline" disabled={!debt} onClick={() => setDueDateModalOpen(true)}>
              <CalendarClock />
              Muddatni o'zgartirish
            </Button>
            <Button disabled={!debt || debt.status === "paid"} onClick={() => setPaymentModalOpen(true)}>
              <Plus />
              To'lov qo'shish
            </Button>
          </div>
        }
      />

      <div className="mt-6">
        {debtQuery.isError ? (
          <ErrorState onRetry={() => void debtQuery.refetch()} />
        ) : debtQuery.isLoading || !debt ? (
          <div className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 rounded-lg border bg-card p-4 shadow-xs sm:grid-cols-2 lg:grid-cols-4">
              <Field label="Boshlanish sanasi" value={formatDate(debt.start_date)} />
              <Field label="Muddati" value={debt.due_date ? formatDate(debt.due_date) : "—"} />
              <Field
                label="Holati"
                value={
                  <Badge variant={statusVariant[debt.status]} dot>
                    {statusLabels[debt.status]}
                  </Badge>
                }
              />
              <Field label="Summasi" value={formatMoney(debt.amount)} />
              <Field label="To'langan" value={formatMoney(debt.paid_amount)} />
              <Field label="Qoldiq" value={<span className="font-medium">{formatMoney(debt.remaining_amount)}</span>} />
              {debt.note ? (
                <div className="sm:col-span-2 lg:col-span-4">
                  <Field label="Izoh" value={debt.note} />
                </div>
              ) : null}
            </div>

            <div>
              <h2 className="mb-3 text-sm font-medium text-foreground">To'lovlar tarixi</h2>
              <div className="overflow-hidden rounded-lg border bg-card shadow-xs">
                {debt.payments.length === 0 ? (
                  <EmptyState compact title="Hozircha to'lovlar yo'q" />
                ) : (
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
                        {debt.payments.map((payment) => (
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
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <Modal
        open={paymentModalOpen}
        onOpenChange={setPaymentModalOpen}
        title="To'lov qo'shish"
        footer={
          <>
            <Button variant="outline" onClick={() => setPaymentModalOpen(false)}>
              Bekor qilish
            </Button>
            <Button onClick={paymentForm.handleSubmit((v) => paymentMutation.mutate(v))} loading={paymentMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={paymentForm.handleSubmit((v) => paymentMutation.mutate(v))}>
          <FormField htmlFor="debt-payment-amount" label="Summasi" required error={paymentForm.formState.errors.amount?.message}>
            <Input id="debt-payment-amount" type="number" step="0.01" invalid={!!paymentForm.formState.errors.amount} {...paymentForm.register("amount")} />
          </FormField>
          <FormField htmlFor="debt-payment-method" label="To'lov turi" required error={paymentForm.formState.errors.payment_method_id?.message}>
            <Select
              id="debt-payment-method"
              options={paymentMethodOptions}
              placeholder="Tanlang…"
              invalid={!!paymentForm.formState.errors.payment_method_id}
              {...paymentForm.register("payment_method_id")}
            />
          </FormField>
          <FormField htmlFor="debt-payment-note" label="Izoh">
            <Input id="debt-payment-note" {...paymentForm.register("note")} />
          </FormField>
        </form>
      </Modal>

      <Modal
        open={dueDateModalOpen}
        onOpenChange={setDueDateModalOpen}
        title="Qarz muddatini o'zgartirish"
        footer={
          <>
            <Button variant="outline" onClick={() => setDueDateModalOpen(false)}>
              Bekor qilish
            </Button>
            <Button onClick={dueDateForm.handleSubmit((v) => dueDateMutation.mutate(v))} loading={dueDateMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={dueDateForm.handleSubmit((v) => dueDateMutation.mutate(v))}>
          <FormField htmlFor="debt-due-date" label="Muddati">
            <Input id="debt-due-date" type="date" {...dueDateForm.register("due_date")} />
          </FormField>
        </form>
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

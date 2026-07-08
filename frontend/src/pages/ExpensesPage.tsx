import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { formatDate, formatMoney } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { expenseService } from "@/services/expense";
import { storeService } from "@/services/store";
import type { ExpenseListParams, ExpenseType } from "@/types/expense";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";

const expenseTypeOptions = [
  { label: "Yoqilg'i", value: "fuel" },
  { label: "Haydovchi", value: "driver" },
  { label: "Yuk tashuvchi", value: "loader" },
  { label: "Boshqa", value: "other" },
];

const expenseTypeLabels: Record<ExpenseType, string> = {
  fuel: "Yoqilg'i",
  driver: "Haydovchi",
  loader: "Yuk tashuvchi",
  other: "Boshqa",
};

const expenseFormSchema = z.object({
  store_id: z.string().optional(),
  expense_type: z.enum(["fuel", "driver", "loader", "other"], { required_error: "Turini tanlash shart" }),
  amount: z.coerce.number({ invalid_type_error: "Summasi raqam bo'lishi kerak" }).positive("0 dan katta bo'lishi kerak"),
  description: z.string().min(1, "Tavsif to'ldirilishi shart"),
  date: z.string().optional(),
});
type ExpenseFormSchemaValues = z.infer<typeof expenseFormSchema>;

export default function ExpensesPage() {
  const { user } = useAuth();
  // Only an actual CEO must supply store_id; the legacy single-tenant admin
  // resolves to (None, None) and never needs a store (see Stock In).
  const isCeo = user?.role === "ceo";
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = React.useState(false);

  const [storeId, setStoreId] = React.useState("");
  const [expenseType, setExpenseType] = React.useState("");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [page, setPage] = React.useState(1);

  const params: ExpenseListParams = {
    ...(storeId ? { store_id: Number(storeId) } : {}),
    ...(expenseType ? { expense_type: expenseType as ExpenseType } : {}),
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
    page,
  };

  React.useEffect(() => {
    setPage(1);
  }, [storeId, expenseType, dateFrom, dateTo]);

  const expensesQuery = useQuery({ queryKey: ["expenses", params], queryFn: () => expenseService.list(params) });
  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });

  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
  );

  const form = useForm<ExpenseFormSchemaValues>({
    resolver: zodResolver(expenseFormSchema),
    defaultValues: { store_id: "", expense_type: "other", amount: 0, description: "", date: "" },
  });

  const createMutation = useMutation({
    mutationFn: expenseService.create,
    onSuccess: () => {
      toast.success("Xarajat qo'shildi.");
      setModalOpen(false);
      form.reset({ store_id: "", expense_type: "other", amount: 0, description: "", date: "" });
      void queryClient.invalidateQueries({ queryKey: ["expenses"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: toastMutationError,
  });

  const onSubmit = (values: ExpenseFormSchemaValues) => {
    if (isCeo && !values.store_id) {
      form.setError("store_id", { message: "Do'konni tanlash shart" });
      return;
    }
    createMutation.mutate(values);
  };

  const items = expensesQuery.data?.items ?? [];
  const total = items.reduce((sum, e) => sum + Number(e.amount), 0);

  return (
    <ContentContainer>
      <PageHeader
        title="Xarajatlar"
        description="Do'kon xarajatlari qaydi. Saqlangan xarajatlarni tahrirlab yoki o'chirib bo'lmaydi."
        actions={
          <Button onClick={() => setModalOpen(true)}>
            <Plus />
            Xarajat qo'shish
          </Button>
        }
      />

      <div className="mt-6 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Select
            options={expenseTypeOptions}
            placeholder="Barcha turlar"
            value={expenseType}
            onChange={(e) => setExpenseType(e.target.value)}
            className="w-48"
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
          {expensesQuery.isError ? (
            <ErrorState error={expensesQuery.error} onRetry={() => void expensesQuery.refetch()} />
          ) : expensesQuery.isLoading ? (
            <TableSkeleton />
          ) : items.length === 0 ? (
            <EmptyState
              title="Hozircha xarajatlar yo'q"
              description="Boshlash uchun birinchi xarajatingizni qo'shing."
              action={<Button size="sm" onClick={() => setModalOpen(true)}>Xarajat qo'shish</Button>}
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Sana</TableHead>
                    <TableHead>Turi</TableHead>
                    <TableHead>Tavsif</TableHead>
                    <TableHead>Yaratgan xodim</TableHead>
                    <TableHead className="text-right">Summasi</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((expense) => (
                    <TableRow key={expense.id}>
                      <TableCell className="text-muted-foreground">{formatDate(expense.date)}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{expenseTypeLabels[expense.expense_type]}</Badge>
                      </TableCell>
                      <TableCell>{expense.description}</TableCell>
                      <TableCell className="text-muted-foreground">{expense.created_by?.full_name ?? "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatMoney(expense.amount)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="flex justify-end border-t border-border/70 px-5 py-3">
                <p className="text-sm">
                  <span className="text-muted-foreground">Joriy sahifa jami: </span>
                  <span className="font-medium tabular-nums">{formatMoney(total)}</span>
                </p>
              </div>
            </div>
          )}
          {expensesQuery.data ? <Pagination meta={expensesQuery.data.meta} onPageChange={setPage} /> : null}
        </TableCard>
      </div>

      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title="Xarajat qo'shish"
        footer={
          <>
            <Button variant="outline" onClick={() => setModalOpen(false)}>
              Bekor qilish
            </Button>
            <Button onClick={form.handleSubmit(onSubmit)} loading={createMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          {isCeo ? (
            <FormField htmlFor="expense-store" label="Do'kon" required error={form.formState.errors.store_id?.message}>
              <Select id="expense-store" options={storeOptions} placeholder="Do'konni tanlang…" invalid={!!form.formState.errors.store_id} {...form.register("store_id")} />
            </FormField>
          ) : null}
          <FormField htmlFor="expense-type" label="Turi" required>
            <Select id="expense-type" options={expenseTypeOptions} {...form.register("expense_type")} />
          </FormField>
          <FormField htmlFor="expense-amount" label="Summasi" required error={form.formState.errors.amount?.message}>
            <Input id="expense-amount" type="number" step="0.01" invalid={!!form.formState.errors.amount} {...form.register("amount")} />
          </FormField>
          <FormField htmlFor="expense-description" label="Tavsif" required error={form.formState.errors.description?.message}>
            <Input id="expense-description" invalid={!!form.formState.errors.description} {...form.register("description")} />
          </FormField>
          <FormField htmlFor="expense-date" label="Sana">
            <Input id="expense-date" type="date" {...form.register("date")} />
          </FormField>
        </form>
      </Modal>
    </ContentContainer>
  );
}

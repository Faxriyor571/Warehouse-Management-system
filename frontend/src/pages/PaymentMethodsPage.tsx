import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { useAuth } from "@/providers/auth-provider";
import { paymentMethodService } from "@/services/payment-method";
import type { PaymentMethod } from "@/types/payment-method";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";
import { SwitchField } from "@/components/forms/switch-field";

const typeOptions = [
  { label: "Naqd", value: "cash" },
  { label: "Click", value: "click" },
  { label: "Payme", value: "payme" },
  { label: "Bank", value: "bank" },
  { label: "Qarz", value: "debt" },
];

const typeLabels: Record<string, string> = {
  cash: "Naqd",
  click: "Click",
  payme: "Payme",
  bank: "Bank",
  debt: "Qarz",
};

const formSchema = z.object({
  name: z.string().min(1, "Nomi to'ldirilishi shart"),
  type: z.enum(["cash", "click", "payme", "bank", "debt"], { required_error: "Turini tanlash shart" }),
  is_active: z.boolean(),
});
type FormValues = z.infer<typeof formSchema>;

type ModalState = "new" | PaymentMethod | null;

export default function PaymentMethodsPage() {
  const { user } = useAuth();
  // Manage (create/update/delete) is CEO-only, or the legacy admin
  // (role === null) — see require_payment_method_manage in
  // app/auth/legacy_compat.py. A Seller has read-only access (needed for
  // the Sales payment picker), so this page is reachable for them via
  // direct URL/sidebar, but write actions must be hidden, not just
  // rejected server-side.
  const canManage = user?.role === "ceo" || user?.role == null;
  const queryClient = useQueryClient();
  const [modalMethod, setModalMethod] = React.useState<ModalState>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<PaymentMethod | null>(null);

  const methodsQuery = useQuery({ queryKey: ["payment-methods"], queryFn: paymentMethodService.list });

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: "", type: "cash", is_active: true },
  });

  React.useEffect(() => {
    if (modalMethod && modalMethod !== "new") {
      form.reset({ name: modalMethod.name, type: modalMethod.type as FormValues["type"], is_active: modalMethod.is_active });
    } else if (modalMethod === "new") {
      form.reset({ name: "", type: "cash", is_active: true });
    }
  }, [modalMethod, form]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["payment-methods"] });

  const createMutation = useMutation({
    mutationFn: paymentMethodService.create,
    onSuccess: () => {
      toast.success("To'lov turi yaratildi.");
      setModalMethod(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: FormValues }) => paymentMethodService.update(id, values),
    onSuccess: () => {
      toast.success("To'lov turi yangilandi.");
      setModalMethod(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const deleteMutation = useMutation({
    mutationFn: paymentMethodService.remove,
    onSuccess: () => {
      toast.success("To'lov turi o'chirildi.");
      setDeleteTarget(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const onSubmit = (values: FormValues) => {
    if (modalMethod === "new") createMutation.mutate(values);
    else if (modalMethod) updateMutation.mutate({ id: modalMethod.id, values });
  };

  const isEditing = modalMethod !== null;
  const methods = methodsQuery.data ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="To'lov turlari"
        description="Savdo va qarz to'lovlarida ishlatiladigan to'lov turlari."
        actions={
          canManage ? (
            <Button onClick={() => setModalMethod("new")}>
              <Plus />
              Yangi to'lov turi
            </Button>
          ) : null
        }
      />

      <TableCard className="mt-6">
        {methodsQuery.isError ? (
          <ErrorState error={methodsQuery.error} onRetry={() => void methodsQuery.refetch()} />
        ) : methodsQuery.isLoading ? (
          <TableSkeleton />
        ) : methods.length === 0 ? (
          <EmptyState
            title="Hozircha to'lov turlari yo'q"
            description="Boshlash uchun birinchi to'lov turingizni qo'shing."
            action={canManage ? <Button size="sm" onClick={() => setModalMethod("new")}>Yangi to'lov turi</Button> : undefined}
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Nomi</TableHead>
                <TableHead>Turi</TableHead>
                <TableHead>Holati</TableHead>
                {canManage ? <TableHead className="text-right" /> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {methods.map((method) => (
                <TableRow key={method.id}>
                  <TableCell className="font-medium">
                    {method.name}
                    {method.is_system ? <Badge variant="outline" className="ml-2">Tizim</Badge> : null}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{typeLabels[method.type] ?? method.type}</TableCell>
                  <TableCell>
                    <Badge variant={method.is_active ? "success" : "secondary"} dot>
                      {method.is_active ? "Faol" : "Nofaol"}
                    </Badge>
                  </TableCell>
                  {canManage ? (
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1.5">
                        <Button variant="ghost" size="icon-sm" onClick={() => setModalMethod(method)} aria-label="Tahrirlash">
                          <Pencil className="size-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          disabled={method.is_system}
                          onClick={() => setDeleteTarget(method)}
                          aria-label="O'chirish"
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </TableCell>
                  ) : null}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableCard>

      <Modal
        open={isEditing}
        onOpenChange={(open) => !open && setModalMethod(null)}
        title={modalMethod === "new" ? "Yangi to'lov turi" : "To'lov turini tahrirlash"}
        footer={
          <>
            <Button variant="outline" onClick={() => setModalMethod(null)}>
              Bekor qilish
            </Button>
            <Button onClick={form.handleSubmit(onSubmit)} loading={createMutation.isPending || updateMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <FormField htmlFor="pm-name" label="Nomi" required error={form.formState.errors.name?.message}>
            <Input id="pm-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
          </FormField>
          <FormField htmlFor="pm-type" label="Turi" required>
            <Select
              id="pm-type"
              options={typeOptions}
              disabled={modalMethod !== "new" && modalMethod?.is_system}
              {...form.register("type")}
            />
          </FormField>
          <SwitchField
            control={form.control}
            name="is_active"
            htmlFor="pm-active"
            label="Faol"
            description="Nofaol to'lov turlari yangi savdolarda tanlab bo'lmaydi."
          />
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`${deleteTarget?.name} o'chirilsinmi?`}
        description="Ushbu to'lov turi butunlay o'chiriladi."
        confirmLabel="O'chirish"
        variant="destructive"
        loading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </ContentContainer>
  );
}

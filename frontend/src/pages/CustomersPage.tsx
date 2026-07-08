import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { Pencil, Plus, Power } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { getErrorMessage } from "@/lib/http";
import { useAuth } from "@/providers/auth-provider";
import { customerService } from "@/services/customer";
import type { Customer } from "@/types/customer";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

const customerTypeOptions = [
  { label: "Jismoniy shaxs", value: "individual" },
  { label: "Yuridik shaxs", value: "legal_entity" },
];

const customerFormSchema = z.object({
  full_name: z.string().min(2, "F.I.Sh. kamida 2 belgidan iborat bo'lishi kerak"),
  customer_type: z.enum(["individual", "legal_entity"], { required_error: "Mijoz turini tanlash shart" }),
  phone: z.string().optional(),
  address: z.string().optional(),
  passport: z.string().optional(),
  description: z.string().optional(),
  is_active: z.boolean(),
});
type CustomerFormValues = z.infer<typeof customerFormSchema>;

type ModalState = "new" | Customer | null;

const typeLabels: Record<string, string> = { individual: "Jismoniy shaxs", legal_entity: "Yuridik shaxs" };

export default function CustomersPage() {
  const { user } = useAuth();
  const isCeo = user?.role === "ceo" || user?.role == null;
  const queryClient = useQueryClient();
  const [modalCustomer, setModalCustomer] = React.useState<ModalState>(null);
  const [deactivateTarget, setDeactivateTarget] = React.useState<Customer | null>(null);

  const customersQuery = useQuery({ queryKey: ["customers"], queryFn: customerService.list });

  const form = useForm<CustomerFormValues>({
    resolver: zodResolver(customerFormSchema),
    defaultValues: { full_name: "", customer_type: "individual", phone: "", address: "", passport: "", description: "", is_active: true },
  });

  React.useEffect(() => {
    if (modalCustomer && modalCustomer !== "new") {
      form.reset({
        full_name: modalCustomer.full_name,
        customer_type: modalCustomer.customer_type ?? "individual",
        phone: modalCustomer.phone ?? "",
        address: modalCustomer.address ?? "",
        passport: modalCustomer.passport ?? "",
        description: modalCustomer.description ?? "",
        is_active: modalCustomer.is_active,
      });
    } else if (modalCustomer === "new") {
      form.reset({ full_name: "", customer_type: "individual", phone: "", address: "", passport: "", description: "", is_active: true });
    }
  }, [modalCustomer, form]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["customers"] });

  const createMutation = useMutation({
    mutationFn: customerService.create,
    onSuccess: () => {
      toast.success("Mijoz yaratildi.");
      setModalCustomer(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: CustomerFormValues }) => customerService.update(id, values),
    onSuccess: () => {
      toast.success("Mijoz yangilandi.");
      setModalCustomer(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const deactivateMutation = useMutation({
    mutationFn: customerService.deactivate,
    onSuccess: () => {
      toast.success("Mijoz faolsizlantirildi.");
      setDeactivateTarget(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const onSubmit = (values: CustomerFormValues) => {
    if (modalCustomer === "new") createMutation.mutate(values);
    else if (modalCustomer) updateMutation.mutate({ id: modalCustomer.id, values });
  };

  const isEditing = modalCustomer !== null;
  const customers = customersQuery.data ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Mijozlar"
        description="Kompaniyangiz mahsulot sotadigan mijozlarni boshqaring."
        actions={
          <Button onClick={() => setModalCustomer("new")}>
            <Plus />
            Yangi mijoz
          </Button>
        }
      />

      <div className="mt-6 overflow-hidden rounded-lg border">
        {customersQuery.isError ? (
          <ErrorState onRetry={() => void customersQuery.refetch()} />
        ) : customersQuery.isLoading ? (
          <div className="space-y-3 p-6">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : customers.length === 0 ? (
          <EmptyState title="Hozircha mijozlar yo'q" description="Boshlash uchun birinchi mijozingizni qo'shing." />
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-6 py-2 text-left font-medium">F.I.Sh.</th>
                <th className="px-6 py-2 text-left font-medium">Turi</th>
                <th className="px-6 py-2 text-left font-medium">Telefon</th>
                <th className="px-6 py-2 text-left font-medium">Holati</th>
                <th className="px-6 py-2 text-right font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {customers.map((customer) => (
                <tr key={customer.id}>
                  <td className="px-6 py-2.5 font-medium">{customer.full_name}</td>
                  <td className="px-6 py-2.5 text-muted-foreground">
                    {customer.customer_type ? typeLabels[customer.customer_type] : "—"}
                  </td>
                  <td className="px-6 py-2.5 text-muted-foreground">{customer.phone ?? "—"}</td>
                  <td className="px-6 py-2.5">
                    <Badge variant={customer.is_active ? "success" : "secondary"} dot>
                      {customer.is_active ? "Faol" : "Nofaol"}
                    </Badge>
                  </td>
                  <td className="px-6 py-2.5">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => setModalCustomer(customer)} aria-label="Tahrirlash">
                        <Pencil className="size-4" />
                      </Button>
                      {isCeo ? (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          disabled={!customer.is_active}
                          onClick={() => setDeactivateTarget(customer)}
                          aria-label="Faolsizlantirish"
                        >
                          <Power className="size-4" />
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal
        open={isEditing}
        onOpenChange={(open) => !open && setModalCustomer(null)}
        title={modalCustomer === "new" ? "Yangi mijoz" : "Mijozni tahrirlash"}
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setModalCustomer(null)}>
              Bekor qilish
            </Button>
            <Button onClick={form.handleSubmit(onSubmit)} loading={createMutation.isPending || updateMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="customer-name" required>
                F.I.Sh.
              </Label>
              <Input id="customer-name" invalid={!!form.formState.errors.full_name} {...form.register("full_name")} />
              {form.formState.errors.full_name ? (
                <p className="text-sm text-destructive">{form.formState.errors.full_name.message}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="customer-type" required>
                Mijoz turi
              </Label>
              <Select id="customer-type" options={customerTypeOptions} {...form.register("customer_type")} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="customer-phone">Telefon</Label>
              <Input id="customer-phone" placeholder="+998901234567" {...form.register("phone")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="customer-passport">Pasport</Label>
              <Input id="customer-passport" {...form.register("passport")} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="customer-address">Manzil</Label>
            <Input id="customer-address" {...form.register("address")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="customer-description">Tavsif</Label>
            <Input id="customer-description" {...form.register("description")} />
          </div>
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div className="space-y-0.5">
              <Label htmlFor="customer-active">Faol</Label>
              <p className="text-sm text-muted-foreground">Nofaol mijozlar yangi savdolarda ko'rinmaydi.</p>
            </div>
            <Controller
              control={form.control}
              name="is_active"
              render={({ field }) => <Switch id="customer-active" checked={field.value} onCheckedChange={field.onChange} />}
            />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={deactivateTarget !== null}
        onOpenChange={(open) => !open && setDeactivateTarget(null)}
        title={`${deactivateTarget?.full_name} faolsizlantirilsinmi?`}
        description="Qarzdorligi bor mijozlarni faolsizlantirib bo'lmaydi."
        confirmLabel="Faolsizlantirish"
        variant="destructive"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateTarget && deactivateMutation.mutate(deactivateTarget.id)}
      />
    </ContentContainer>
  );
}

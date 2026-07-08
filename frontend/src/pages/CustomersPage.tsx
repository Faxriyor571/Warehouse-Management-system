import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
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
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/FormField";
import { SwitchField } from "@/components/forms/SwitchField";

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

      <div className="mt-6 overflow-hidden rounded-lg border bg-card shadow-xs">
        {customersQuery.isError ? (
          <ErrorState onRetry={() => void customersQuery.refetch()} />
        ) : customersQuery.isLoading ? (
          <TableSkeleton />
        ) : customers.length === 0 ? (
          <EmptyState
            title="Hozircha mijozlar yo'q"
            description="Boshlash uchun birinchi mijozingizni qo'shing."
            action={<Button size="sm" onClick={() => setModalCustomer("new")}>Yangi mijoz</Button>}
          />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>F.I.Sh.</TableHead>
                  <TableHead>Turi</TableHead>
                  <TableHead>Telefon</TableHead>
                  <TableHead>Holati</TableHead>
                  <TableHead className="text-right" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {customers.map((customer) => (
                  <TableRow key={customer.id}>
                    <TableCell className="font-medium">{customer.full_name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {customer.customer_type ? typeLabels[customer.customer_type] : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{customer.phone ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant={customer.is_active ? "success" : "secondary"} dot>
                        {customer.is_active ? "Faol" : "Nofaol"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
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
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
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
            <FormField htmlFor="customer-name" label="F.I.Sh." required error={form.formState.errors.full_name?.message}>
              <Input id="customer-name" invalid={!!form.formState.errors.full_name} {...form.register("full_name")} />
            </FormField>
            <FormField htmlFor="customer-type" label="Mijoz turi" required>
              <Select id="customer-type" options={customerTypeOptions} {...form.register("customer_type")} />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField htmlFor="customer-phone" label="Telefon">
              <Input id="customer-phone" placeholder="+998901234567" {...form.register("phone")} />
            </FormField>
            <FormField htmlFor="customer-passport" label="Pasport">
              <Input id="customer-passport" {...form.register("passport")} />
            </FormField>
          </div>
          <FormField htmlFor="customer-address" label="Manzil">
            <Input id="customer-address" {...form.register("address")} />
          </FormField>
          <FormField htmlFor="customer-description" label="Tavsif">
            <Input id="customer-description" {...form.register("description")} />
          </FormField>
          <SwitchField
            control={form.control}
            name="is_active"
            htmlFor="customer-active"
            label="Faol"
            description="Nofaol mijozlar yangi savdolarda ko'rinmaydi."
          />
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

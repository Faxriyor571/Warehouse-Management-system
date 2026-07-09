import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Power } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
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
import { SegmentedTabs } from "@/components/ui/segmented-tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";
import { SwitchField } from "@/components/forms/switch-field";

const customerTypeOptions = [
  { label: "Jismoniy shaxs", value: "individual" },
  { label: "Yuridik shaxs", value: "legal_entity" },
];

// F.I.Sh. is required for a Legal Entity but optional for an Individual —
// a walk-in individual buyer isn't forced to have a name on file (backend:
// customer_service.create_customer generates a placeholder when omitted).
const customerFormSchema = z
  .object({
    full_name: z.string().optional(),
    customer_type: z.enum(["individual", "legal_entity"], { required_error: "Mijoz turini tanlash shart" }),
    phone: z.string().optional(),
    address: z.string().optional(),
    passport: z.string().optional(),
    description: z.string().optional(),
    is_active: z.boolean(),
  })
  .superRefine((data, ctx) => {
    if (data.customer_type === "legal_entity" && (!data.full_name || data.full_name.trim().length < 2)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["full_name"],
        message: "F.I.Sh. kamida 2 belgidan iborat bo'lishi kerak",
      });
    }
  });
type CustomerFormValues = z.infer<typeof customerFormSchema>;

type ModalState = "new" | Customer | null;

type CustomerTypeTab = "legal_entity" | "individual";
const customerTypeTabs = [
  { id: "legal_entity" as const, label: "Yuridik shaxslar" },
  { id: "individual" as const, label: "Jismoniy shaxslar" },
];

export default function CustomersPage() {
  const { user } = useAuth();
  const isCeo = user?.role === "ceo" || user?.role == null;
  const queryClient = useQueryClient();
  const [tab, setTab] = React.useState<CustomerTypeTab>("legal_entity");
  const [modalCustomer, setModalCustomer] = React.useState<ModalState>(null);
  const [deactivateTarget, setDeactivateTarget] = React.useState<Customer | null>(null);

  const customersQuery = useQuery({ queryKey: ["customers"], queryFn: customerService.list });

  const form = useForm<CustomerFormValues>({
    resolver: zodResolver(customerFormSchema),
    defaultValues: { full_name: "", customer_type: "individual", phone: "", address: "", passport: "", description: "", is_active: true },
  });
  const watchedCustomerType = form.watch("customer_type");
  const isIndividual = watchedCustomerType === "individual";

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
      form.reset({ full_name: "", customer_type: tab, phone: "", address: "", passport: "", description: "", is_active: true });
    }
  }, [modalCustomer, form, tab]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["customers"] });

  const createMutation = useMutation({
    mutationFn: customerService.create,
    onSuccess: () => {
      toast.success("Mijoz yaratildi.");
      setModalCustomer(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: CustomerFormValues }) => customerService.update(id, values),
    onSuccess: () => {
      toast.success("Mijoz yangilandi.");
      setModalCustomer(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const deactivateMutation = useMutation({
    mutationFn: customerService.deactivate,
    onSuccess: () => {
      toast.success("Mijoz faolsizlantirildi.");
      setDeactivateTarget(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const onSubmit = (values: CustomerFormValues) => {
    if (modalCustomer === "new") createMutation.mutate(values);
    else if (modalCustomer) updateMutation.mutate({ id: modalCustomer.id, values });
  };

  const isEditing = modalCustomer !== null;
  // customer_type is nullable (legacy pre-migration customers, see
  // models/customer.py) — bucketed under Individual, matching the form's
  // own default, so they stay visible instead of disappearing from both tabs.
  const customers = (customersQuery.data ?? []).filter((c) => (c.customer_type ?? "individual") === tab);

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

      <SegmentedTabs value={tab} onChange={setTab} options={customerTypeTabs} className="mt-6" />

      <TableCard className="mt-4">
        {customersQuery.isError ? (
          <ErrorState error={customersQuery.error} onRetry={() => void customersQuery.refetch()} />
        ) : customersQuery.isLoading ? (
          <TableSkeleton />
        ) : customers.length === 0 ? (
          <EmptyState
            title={tab === "legal_entity" ? "Hozircha yuridik shaxslar yo'q" : "Hozircha jismoniy shaxslar yo'q"}
            description="Boshlash uchun birinchi mijozingizni qo'shing."
            action={<Button size="sm" onClick={() => setModalCustomer("new")}>Yangi mijoz</Button>}
          />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>F.I.Sh.</TableHead>
                  <TableHead>Telefon</TableHead>
                  <TableHead>Holati</TableHead>
                  <TableHead className="text-right" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {customers.map((customer) => (
                  <TableRow key={customer.id}>
                    <TableCell className="font-medium">{customer.full_name}</TableCell>
                    <TableCell className="text-muted-foreground">{customer.phone ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant={customer.is_active ? "success" : "secondary"} dot>
                        {customer.is_active ? "Faol" : "Nofaol"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1.5">
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
      </TableCard>

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
            <FormField
              htmlFor="customer-name"
              label="F.I.Sh."
              required={!isIndividual}
              error={form.formState.errors.full_name?.message}
              description={isIndividual ? "Jismoniy shaxs uchun ixtiyoriy" : undefined}
            >
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

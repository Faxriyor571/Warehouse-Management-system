import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { getErrorMessage } from "@/lib/http";
import { supplierService } from "@/services/supplier";
import type { Supplier } from "@/types/supplier";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/FormField";
import { SwitchField } from "@/components/forms/SwitchField";

const supplierFormSchema = z.object({
  name: z.string().min(1, "Nomi to'ldirilishi shart"),
  phone: z.string().optional(),
  address: z.string().optional(),
  responsible_person: z.string().optional(),
  description: z.string().optional(),
  is_active: z.boolean(),
});
type SupplierFormValues = z.infer<typeof supplierFormSchema>;

type ModalState = "new" | Supplier | null;

export default function SuppliersPage() {
  const queryClient = useQueryClient();
  const [modalSupplier, setModalSupplier] = React.useState<ModalState>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<Supplier | null>(null);

  const suppliersQuery = useQuery({ queryKey: ["suppliers"], queryFn: supplierService.list });

  const form = useForm<SupplierFormValues>({
    resolver: zodResolver(supplierFormSchema),
    defaultValues: { name: "", phone: "", address: "", responsible_person: "", description: "", is_active: true },
  });

  React.useEffect(() => {
    if (modalSupplier && modalSupplier !== "new") {
      form.reset({
        name: modalSupplier.name,
        phone: modalSupplier.phone ?? "",
        address: modalSupplier.address ?? "",
        responsible_person: modalSupplier.responsible_person ?? "",
        description: modalSupplier.description ?? "",
        is_active: modalSupplier.is_active,
      });
    } else if (modalSupplier === "new") {
      form.reset({ name: "", phone: "", address: "", responsible_person: "", description: "", is_active: true });
    }
  }, [modalSupplier, form]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["suppliers"] });

  const createMutation = useMutation({
    mutationFn: supplierService.create,
    onSuccess: () => {
      toast.success("Yetkazib beruvchi yaratildi.");
      setModalSupplier(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: SupplierFormValues }) => supplierService.update(id, values),
    onSuccess: () => {
      toast.success("Yetkazib beruvchi yangilandi.");
      setModalSupplier(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: supplierService.remove,
    onSuccess: () => {
      toast.success("Yetkazib beruvchi o'chirildi.");
      setDeleteTarget(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const onSubmit = (values: SupplierFormValues) => {
    if (modalSupplier === "new") createMutation.mutate(values);
    else if (modalSupplier) updateMutation.mutate({ id: modalSupplier.id, values });
  };

  const isEditing = modalSupplier !== null;
  const suppliers = suppliersQuery.data ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Yetkazib beruvchilar"
        description="Kompaniyangiz mahsulot xarid qiladigan yetkazib beruvchilarni boshqaring."
        actions={
          <Button onClick={() => setModalSupplier("new")}>
            <Plus />
            Yangi yetkazib beruvchi
          </Button>
        }
      />

      <div className="mt-6 overflow-hidden rounded-lg border bg-card shadow-xs">
        {suppliersQuery.isError ? (
          <ErrorState onRetry={() => void suppliersQuery.refetch()} />
        ) : suppliersQuery.isLoading ? (
          <TableSkeleton />
        ) : suppliers.length === 0 ? (
          <EmptyState
            title="Hozircha yetkazib beruvchilar yo'q"
            description="Boshlash uchun birinchi yetkazib beruvchingizni qo'shing."
            action={<Button size="sm" onClick={() => setModalSupplier("new")}>Yangi yetkazib beruvchi</Button>}
          />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Nomi</TableHead>
                  <TableHead>Telefon</TableHead>
                  <TableHead>Manzil</TableHead>
                  <TableHead>Mas'ul shaxs</TableHead>
                  <TableHead>Holati</TableHead>
                  <TableHead className="text-right" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {suppliers.map((supplier) => (
                  <TableRow key={supplier.id}>
                    <TableCell className="font-medium">{supplier.name}</TableCell>
                    <TableCell className="text-muted-foreground">{supplier.phone ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{supplier.address ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{supplier.responsible_person ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant={supplier.is_active ? "success" : "secondary"} dot>
                        {supplier.is_active ? "Faol" : "Nofaol"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon-sm" onClick={() => setModalSupplier(supplier)} aria-label="Tahrirlash">
                          <Pencil className="size-4" />
                        </Button>
                        <Button variant="ghost" size="icon-sm" onClick={() => setDeleteTarget(supplier)} aria-label="O'chirish">
                          <Trash2 className="size-4" />
                        </Button>
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
        onOpenChange={(open) => !open && setModalSupplier(null)}
        title={modalSupplier === "new" ? "Yangi yetkazib beruvchi" : "Yetkazib beruvchini tahrirlash"}
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setModalSupplier(null)}>
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
            <FormField htmlFor="supplier-name" label="Nomi" required error={form.formState.errors.name?.message}>
              <Input id="supplier-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
            </FormField>
            <FormField htmlFor="supplier-phone" label="Telefon">
              <Input id="supplier-phone" {...form.register("phone")} />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField htmlFor="supplier-address" label="Manzil">
              <Input id="supplier-address" {...form.register("address")} />
            </FormField>
            <FormField htmlFor="supplier-responsible" label="Mas'ul shaxs">
              <Input id="supplier-responsible" {...form.register("responsible_person")} />
            </FormField>
          </div>
          <FormField htmlFor="supplier-description" label="Tavsif">
            <Input id="supplier-description" {...form.register("description")} />
          </FormField>
          <SwitchField
            control={form.control}
            name="is_active"
            htmlFor="supplier-active"
            label="Faol"
            description="Nofaol yetkazib beruvchilar yangi kirim hujjatlarida ko'rinmaydi."
          />
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`${deleteTarget?.name} o'chirilsinmi?`}
        description="Ushbu yetkazib beruvchi hisobingizdan o'chiriladi."
        confirmLabel="O'chirish"
        variant="destructive"
        loading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </ContentContainer>
  );
}

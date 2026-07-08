import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
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
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

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

      <div className="mt-6 overflow-hidden rounded-lg border">
        {suppliersQuery.isError ? (
          <ErrorState onRetry={() => void suppliersQuery.refetch()} />
        ) : suppliersQuery.isLoading ? (
          <div className="space-y-3 p-6">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : suppliers.length === 0 ? (
          <EmptyState title="Hozircha yetkazib beruvchilar yo'q" description="Boshlash uchun birinchi yetkazib beruvchingizni qo'shing." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-6 py-2 text-left font-medium">Nomi</th>
                  <th className="px-6 py-2 text-left font-medium">Telefon</th>
                  <th className="px-6 py-2 text-left font-medium">Manzil</th>
                  <th className="px-6 py-2 text-left font-medium">Mas'ul shaxs</th>
                  <th className="px-6 py-2 text-left font-medium">Holati</th>
                  <th className="px-6 py-2 text-right font-medium" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {suppliers.map((supplier) => (
                  <tr key={supplier.id}>
                    <td className="px-6 py-2.5 font-medium">{supplier.name}</td>
                    <td className="px-6 py-2.5 text-muted-foreground">{supplier.phone ?? "—"}</td>
                    <td className="px-6 py-2.5 text-muted-foreground">{supplier.address ?? "—"}</td>
                    <td className="px-6 py-2.5 text-muted-foreground">{supplier.responsible_person ?? "—"}</td>
                    <td className="px-6 py-2.5">
                      <Badge variant={supplier.is_active ? "success" : "secondary"} dot>
                        {supplier.is_active ? "Faol" : "Nofaol"}
                      </Badge>
                    </td>
                    <td className="px-6 py-2.5">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon-sm" onClick={() => setModalSupplier(supplier)} aria-label="Tahrirlash">
                          <Pencil className="size-4" />
                        </Button>
                        <Button variant="ghost" size="icon-sm" onClick={() => setDeleteTarget(supplier)} aria-label="O'chirish">
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
            <div className="space-y-2">
              <Label htmlFor="supplier-name" required>
                Nomi
              </Label>
              <Input id="supplier-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
              {form.formState.errors.name ? <p className="text-sm text-destructive">{form.formState.errors.name.message}</p> : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="supplier-phone">Telefon</Label>
              <Input id="supplier-phone" {...form.register("phone")} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="supplier-address">Manzil</Label>
              <Input id="supplier-address" {...form.register("address")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="supplier-responsible">Mas'ul shaxs</Label>
              <Input id="supplier-responsible" {...form.register("responsible_person")} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="supplier-description">Tavsif</Label>
            <Input id="supplier-description" {...form.register("description")} />
          </div>
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div className="space-y-0.5">
              <Label htmlFor="supplier-active">Faol</Label>
              <p className="text-sm text-muted-foreground">Nofaol yetkazib beruvchilar yangi kirim hujjatlarida ko'rinmaydi.</p>
            </div>
            <Controller
              control={form.control}
              name="is_active"
              render={({ field }) => <Switch id="supplier-active" checked={field.value} onCheckedChange={field.onChange} />}
            />
          </div>
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

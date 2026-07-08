import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { getErrorMessage } from "@/lib/http";
import { formatNumber } from "@/lib/formatters";
import { unitService } from "@/services/unit";
import type { Unit } from "@/types/unit";
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

const unitFormSchema = z.object({
  name: z.string().min(1, "Nomi to'ldirilishi shart"),
  short_name: z.string().min(1, "Qisqa nomi to'ldirilishi shart"),
  conversion_factor: z.coerce
    .number({ invalid_type_error: "Konversiya koeffitsienti raqam bo'lishi kerak" })
    .nonnegative("0 yoki undan katta bo'lishi kerak")
    .optional(),
  is_active: z.boolean(),
});
type UnitFormValues = z.infer<typeof unitFormSchema>;

type ModalState = "new" | Unit | null;

export default function UnitsPage() {
  const queryClient = useQueryClient();
  const [modalUnit, setModalUnit] = React.useState<ModalState>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<Unit | null>(null);

  const unitsQuery = useQuery({ queryKey: ["units"], queryFn: unitService.list });

  const form = useForm<UnitFormValues>({
    resolver: zodResolver(unitFormSchema),
    defaultValues: { name: "", short_name: "", conversion_factor: undefined, is_active: true },
  });

  React.useEffect(() => {
    if (modalUnit && modalUnit !== "new") {
      form.reset({
        name: modalUnit.name,
        short_name: modalUnit.short_name,
        conversion_factor: modalUnit.conversion_factor != null ? Number(modalUnit.conversion_factor) : undefined,
        is_active: modalUnit.is_active,
      });
    } else if (modalUnit === "new") {
      form.reset({ name: "", short_name: "", conversion_factor: undefined, is_active: true });
    }
  }, [modalUnit, form]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["units"] });

  const createMutation = useMutation({
    mutationFn: unitService.create,
    onSuccess: () => {
      toast.success("Birlik yaratildi.");
      setModalUnit(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: UnitFormValues }) => unitService.update(id, values),
    onSuccess: () => {
      toast.success("Birlik yangilandi.");
      setModalUnit(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: unitService.remove,
    onSuccess: () => {
      toast.success("Birlik o'chirildi.");
      setDeleteTarget(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const onSubmit = (values: UnitFormValues) => {
    if (modalUnit === "new") createMutation.mutate(values);
    else if (modalUnit) updateMutation.mutate({ id: modalUnit.id, values });
  };

  const isEditing = modalUnit !== null;
  const units = unitsQuery.data ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Birliklar"
        description="Kompaniyangizning o'lchov birliklarini boshqaring."
        actions={
          <Button onClick={() => setModalUnit("new")}>
            <Plus />
            Yangi birlik
          </Button>
        }
      />

      <div className="mt-6 overflow-hidden rounded-lg border">
        {unitsQuery.isError ? (
          <ErrorState onRetry={() => void unitsQuery.refetch()} />
        ) : unitsQuery.isLoading ? (
          <div className="space-y-3 p-6">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : units.length === 0 ? (
          <EmptyState title="Hozircha birliklar yo'q" description="Boshlash uchun birinchi birligingizni yarating." />
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-6 py-2 text-left font-medium">Nomi</th>
                <th className="px-6 py-2 text-left font-medium">Qisqa nomi</th>
                <th className="px-6 py-2 text-right font-medium">Konversiya koeffitsienti</th>
                <th className="px-6 py-2 text-left font-medium">Holati</th>
                <th className="px-6 py-2 text-right font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {units.map((unit) => (
                <tr key={unit.id}>
                  <td className="px-6 py-2.5 font-medium">{unit.name}</td>
                  <td className="px-6 py-2.5 text-muted-foreground">{unit.short_name}</td>
                  <td className="px-6 py-2.5 text-right tabular-nums">
                    {unit.conversion_factor == null ? "—" : formatNumber(unit.conversion_factor, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-2.5">
                    <Badge variant={unit.is_active ? "success" : "secondary"} dot>
                      {unit.is_active ? "Faol" : "Nofaol"}
                    </Badge>
                  </td>
                  <td className="px-6 py-2.5">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => setModalUnit(unit)} aria-label="Tahrirlash">
                        <Pencil className="size-4" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => setDeleteTarget(unit)} aria-label="O'chirish">
                        <Trash2 className="size-4" />
                      </Button>
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
        onOpenChange={(open) => !open && setModalUnit(null)}
        title={modalUnit === "new" ? "Yangi birlik" : "Birlikni tahrirlash"}
        footer={
          <>
            <Button variant="outline" onClick={() => setModalUnit(null)}>
              Bekor qilish
            </Button>
            <Button onClick={form.handleSubmit(onSubmit)} loading={createMutation.isPending || updateMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="space-y-2">
            <Label htmlFor="unit-name" required>
              Nomi
            </Label>
            <Input id="unit-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
            {form.formState.errors.name ? <p className="text-sm text-destructive">{form.formState.errors.name.message}</p> : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="unit-short-name" required>
              Qisqa nomi
            </Label>
            <Input id="unit-short-name" invalid={!!form.formState.errors.short_name} {...form.register("short_name")} />
            {form.formState.errors.short_name ? (
              <p className="text-sm text-destructive">{form.formState.errors.short_name.message}</p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="unit-conversion">Konversiya koeffitsienti</Label>
            <Input id="unit-conversion" type="number" step="0.01" {...form.register("conversion_factor")} />
          </div>
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div className="space-y-0.5">
              <Label htmlFor="unit-active">Faol</Label>
              <p className="text-sm text-muted-foreground">Nofaol birliklar yangi mahsulotlarda ko'rinmaydi.</p>
            </div>
            <Controller
              control={form.control}
              name="is_active"
              render={({ field }) => <Switch id="unit-active" checked={field.value} onCheckedChange={field.onChange} />}
            />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`${deleteTarget?.name} o'chirilsinmi?`}
        description="Bu birlik butunlay o'chiriladi. Mahsulotda ishlatilayotgan birliklarni o'chirib bo'lmaydi."
        confirmLabel="O'chirish"
        variant="destructive"
        loading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </ContentContainer>
  );
}

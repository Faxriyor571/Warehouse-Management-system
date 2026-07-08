import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Power } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { getErrorMessage } from "@/lib/http";
import { useAuth } from "@/providers/auth-provider";
import { storeService } from "@/services/store";
import type { Store } from "@/types/store";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

const storeFormSchema = z.object({
  name: z.string().min(2, "Nomi kamida 2 belgidan iborat bo'lishi kerak"),
  address: z.string().optional(),
  phone: z.string().optional(),
});
type StoreFormValues = z.infer<typeof storeFormSchema>;

type ModalState = "new" | Store | null;

export default function StoresPage() {
  const { user } = useAuth();
  const isCeo = user?.role === "ceo";
  const queryClient = useQueryClient();
  const [modalStore, setModalStore] = React.useState<ModalState>(null);
  const [deactivateTarget, setDeactivateTarget] = React.useState<Store | null>(null);

  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list });

  const form = useForm<StoreFormValues>({
    resolver: zodResolver(storeFormSchema),
    defaultValues: { name: "", address: "", phone: "" },
  });

  React.useEffect(() => {
    if (modalStore && modalStore !== "new") {
      form.reset({ name: modalStore.name, address: modalStore.address ?? "", phone: modalStore.phone ?? "" });
    } else if (modalStore === "new") {
      form.reset({ name: "", address: "", phone: "" });
    }
  }, [modalStore, form]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["stores"] });

  const createMutation = useMutation({
    mutationFn: storeService.create,
    onSuccess: () => {
      toast.success("Do'kon yaratildi.");
      setModalStore(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: StoreFormValues }) => storeService.update(id, data),
    onSuccess: () => {
      toast.success("Do'kon yangilandi.");
      setModalStore(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const deactivateMutation = useMutation({
    mutationFn: storeService.deactivate,
    onSuccess: () => {
      toast.success("Do'kon faolsizlantirildi.");
      setDeactivateTarget(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const onSubmit = (values: StoreFormValues) => {
    if (modalStore === "new") createMutation.mutate(values);
    else if (modalStore) updateMutation.mutate({ id: modalStore.id, data: values });
  };

  const isEditing = modalStore !== null;
  const stores = storesQuery.data ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Do'konlar"
        description={isCeo ? "Kompaniyangizdagi do'konlarni boshqaring." : "Kompaniyangizdagi do'konlar."}
        actions={
          isCeo ? (
            <Button onClick={() => setModalStore("new")}>
              <Plus />
              Yangi do'kon
            </Button>
          ) : null
        }
      />

      <div className="mt-6 overflow-hidden rounded-lg border">
        {storesQuery.isError ? (
          <ErrorState onRetry={() => void storesQuery.refetch()} />
        ) : storesQuery.isLoading ? (
          <div className="space-y-3 p-6">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : stores.length === 0 ? (
          <EmptyState
            title="Hozircha do'konlar yo'q"
            description={isCeo ? "Boshlash uchun birinchi do'koningizni yarating." : "Do'konlar topilmadi."}
          />
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-6 py-2 text-left font-medium">Nomi</th>
                {isCeo ? (
                  <>
                    <th className="px-6 py-2 text-left font-medium">Manzil</th>
                    <th className="px-6 py-2 text-left font-medium">Telefon</th>
                    <th className="px-6 py-2 text-left font-medium">Holati</th>
                    <th className="px-6 py-2 text-right font-medium" />
                  </>
                ) : null}
              </tr>
            </thead>
            <tbody className="divide-y">
              {stores.map((store) => (
                <tr key={store.id}>
                  <td className="px-6 py-2.5 font-medium">{store.name}</td>
                  {isCeo ? (
                    <>
                      <td className="px-6 py-2.5 text-muted-foreground">{store.address ?? "—"}</td>
                      <td className="px-6 py-2.5 text-muted-foreground">{store.phone ?? "—"}</td>
                      <td className="px-6 py-2.5">
                        <Badge variant={store.is_active ? "success" : "secondary"} dot>
                          {store.is_active ? "Faol" : "Nofaol"}
                        </Badge>
                      </td>
                      <td className="px-6 py-2.5">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon-sm" onClick={() => setModalStore(store)} aria-label="Tahrirlash">
                            <Pencil className="size-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            disabled={!store.is_active}
                            onClick={() => setDeactivateTarget(store)}
                            aria-label="Faolsizlantirish"
                          >
                            <Power className="size-4" />
                          </Button>
                        </div>
                      </td>
                    </>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal
        open={isEditing}
        onOpenChange={(open) => !open && setModalStore(null)}
        title={modalStore === "new" ? "Yangi do'kon" : "Do'konni tahrirlash"}
        footer={
          <>
            <Button variant="outline" onClick={() => setModalStore(null)}>
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
            <Label htmlFor="store-name" required>
              Nomi
            </Label>
            <Input id="store-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
            {form.formState.errors.name ? (
              <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="store-address">Manzil</Label>
            <Input id="store-address" {...form.register("address")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="store-phone">Telefon</Label>
            <Input id="store-phone" {...form.register("phone")} />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={deactivateTarget !== null}
        onOpenChange={(open) => !open && setDeactivateTarget(null)}
        title={`${deactivateTarget?.name} faolsizlantirilsinmi?`}
        description="Do'kon endi yangi amaliyotlar uchun ishlatib bo'lmaydi."
        confirmLabel="Faolsizlantirish"
        variant="destructive"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateTarget && deactivateMutation.mutate(deactivateTarget.id)}
      />
    </ContentContainer>
  );
}

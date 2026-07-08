import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Power } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { useAuth } from "@/providers/auth-provider";
import { storeService } from "@/services/store";
import type { Store } from "@/types/store";
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
import { FormField } from "@/components/forms/form-field";

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
    onError: toastMutationError,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: StoreFormValues }) => storeService.update(id, data),
    onSuccess: () => {
      toast.success("Do'kon yangilandi.");
      setModalStore(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const deactivateMutation = useMutation({
    mutationFn: storeService.deactivate,
    onSuccess: () => {
      toast.success("Do'kon faolsizlantirildi.");
      setDeactivateTarget(null);
      void invalidate();
    },
    onError: toastMutationError,
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

      <div className="mt-6 overflow-hidden rounded-lg border bg-card shadow-xs">
        {storesQuery.isError ? (
          <ErrorState error={storesQuery.error} onRetry={() => void storesQuery.refetch()} />
        ) : storesQuery.isLoading ? (
          <TableSkeleton />
        ) : stores.length === 0 ? (
          <EmptyState
            title="Hozircha do'konlar yo'q"
            description={isCeo ? "Boshlash uchun birinchi do'koningizni yarating." : "Do'konlar topilmadi."}
            action={isCeo ? <Button size="sm" onClick={() => setModalStore("new")}>Yangi do'kon</Button> : undefined}
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Nomi</TableHead>
                {isCeo ? (
                  <>
                    <TableHead>Manzil</TableHead>
                    <TableHead>Telefon</TableHead>
                    <TableHead>Holati</TableHead>
                    <TableHead className="text-right" />
                  </>
                ) : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {stores.map((store) => (
                <TableRow key={store.id}>
                  <TableCell className="font-medium">{store.name}</TableCell>
                  {isCeo ? (
                    <>
                      <TableCell className="text-muted-foreground">{store.address ?? "—"}</TableCell>
                      <TableCell className="text-muted-foreground">{store.phone ?? "—"}</TableCell>
                      <TableCell>
                        <Badge variant={store.is_active ? "success" : "secondary"} dot>
                          {store.is_active ? "Faol" : "Nofaol"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
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
                      </TableCell>
                    </>
                  ) : null}
                </TableRow>
              ))}
            </TableBody>
          </Table>
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
          <FormField htmlFor="store-name" label="Nomi" required error={form.formState.errors.name?.message}>
            <Input id="store-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
          </FormField>
          <FormField htmlFor="store-address" label="Manzil">
            <Input id="store-address" {...form.register("address")} />
          </FormField>
          <FormField htmlFor="store-phone" label="Telefon">
            <Input id="store-phone" {...form.register("phone")} />
          </FormField>
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

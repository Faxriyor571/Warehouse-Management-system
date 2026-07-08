import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { getErrorMessage } from "@/lib/http";
import { categoryService } from "@/services/category";
import type { Category } from "@/types/category";
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

const categoryFormSchema = z.object({
  name: z.string().min(1, "Nomi to'ldirilishi shart"),
  description: z.string().optional(),
  is_active: z.boolean(),
});
type CategoryFormValues = z.infer<typeof categoryFormSchema>;

type ModalState = "new" | Category | null;

export default function CategoriesPage() {
  const queryClient = useQueryClient();
  const [modalCategory, setModalCategory] = React.useState<ModalState>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<Category | null>(null);

  const categoriesQuery = useQuery({ queryKey: ["categories"], queryFn: categoryService.list });

  const form = useForm<CategoryFormValues>({
    resolver: zodResolver(categoryFormSchema),
    defaultValues: { name: "", description: "", is_active: true },
  });

  React.useEffect(() => {
    if (modalCategory && modalCategory !== "new") {
      form.reset({ name: modalCategory.name, description: modalCategory.description ?? "", is_active: modalCategory.is_active });
    } else if (modalCategory === "new") {
      form.reset({ name: "", description: "", is_active: true });
    }
  }, [modalCategory, form]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["categories"] });

  const createMutation = useMutation({
    mutationFn: categoryService.create,
    onSuccess: () => {
      toast.success("Kategoriya yaratildi.");
      setModalCategory(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: CategoryFormValues }) => categoryService.update(id, values),
    onSuccess: () => {
      toast.success("Kategoriya yangilandi.");
      setModalCategory(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: categoryService.remove,
    onSuccess: () => {
      toast.success("Kategoriya o'chirildi.");
      setDeleteTarget(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const onSubmit = (values: CategoryFormValues) => {
    if (modalCategory === "new") createMutation.mutate(values);
    else if (modalCategory) updateMutation.mutate({ id: modalCategory.id, values });
  };

  const isEditing = modalCategory !== null;
  const categories = categoriesQuery.data ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Kategoriyalar"
        description="Kompaniyangizning mahsulot kategoriyalarini boshqaring."
        actions={
          <Button onClick={() => setModalCategory("new")}>
            <Plus />
            Yangi kategoriya
          </Button>
        }
      />

      <div className="mt-6 overflow-hidden rounded-lg border">
        {categoriesQuery.isError ? (
          <ErrorState onRetry={() => void categoriesQuery.refetch()} />
        ) : categoriesQuery.isLoading ? (
          <div className="space-y-3 p-6">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : categories.length === 0 ? (
          <EmptyState title="Hozircha kategoriyalar yo'q" description="Boshlash uchun birinchi kategoriyangizni yarating." />
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-6 py-2 text-left font-medium">Nomi</th>
                <th className="px-6 py-2 text-left font-medium">Tavsif</th>
                <th className="px-6 py-2 text-left font-medium">Holati</th>
                <th className="px-6 py-2 text-right font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {categories.map((category) => (
                <tr key={category.id}>
                  <td className="px-6 py-2.5 font-medium">{category.name}</td>
                  <td className="px-6 py-2.5 text-muted-foreground">{category.description ?? "—"}</td>
                  <td className="px-6 py-2.5">
                    <Badge variant={category.is_active ? "success" : "secondary"} dot>
                      {category.is_active ? "Faol" : "Nofaol"}
                    </Badge>
                  </td>
                  <td className="px-6 py-2.5">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => setModalCategory(category)} aria-label="Tahrirlash">
                        <Pencil className="size-4" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => setDeleteTarget(category)} aria-label="O'chirish">
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
        onOpenChange={(open) => !open && setModalCategory(null)}
        title={modalCategory === "new" ? "Yangi kategoriya" : "Kategoriyani tahrirlash"}
        footer={
          <>
            <Button variant="outline" onClick={() => setModalCategory(null)}>
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
            <Label htmlFor="category-name" required>
              Nomi
            </Label>
            <Input id="category-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
            {form.formState.errors.name ? <p className="text-sm text-destructive">{form.formState.errors.name.message}</p> : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="category-description">Tavsif</Label>
            <Input id="category-description" {...form.register("description")} />
          </div>
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div className="space-y-0.5">
              <Label htmlFor="category-active">Faol</Label>
              <p className="text-sm text-muted-foreground">Nofaol kategoriyalar yangi mahsulotlarda ko'rinmaydi.</p>
            </div>
            <Controller
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <Switch id="category-active" checked={field.value} onCheckedChange={field.onChange} />
              )}
            />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`${deleteTarget?.name} o'chirilsinmi?`}
        description="Ushbu kategoriyaga bog'langan mahsulotlarda u saqlanib qoladi, lekin endi tanlab bo'lmaydi."
        confirmLabel="O'chirish"
        variant="destructive"
        loading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </ContentContainer>
  );
}

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { categoryService } from "@/services/category";
import type { Category } from "@/types/category";
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
import { SwitchField } from "@/components/forms/switch-field";

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
    onError: toastMutationError,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: CategoryFormValues }) => categoryService.update(id, values),
    onSuccess: () => {
      toast.success("Kategoriya yangilandi.");
      setModalCategory(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const deleteMutation = useMutation({
    mutationFn: categoryService.remove,
    onSuccess: () => {
      toast.success("Kategoriya o'chirildi.");
      setDeleteTarget(null);
      void invalidate();
    },
    onError: toastMutationError,
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

      <div className="mt-6 overflow-hidden rounded-lg border bg-card shadow-xs">
        {categoriesQuery.isError ? (
          <ErrorState error={categoriesQuery.error} onRetry={() => void categoriesQuery.refetch()} />
        ) : categoriesQuery.isLoading ? (
          <TableSkeleton />
        ) : categories.length === 0 ? (
          <EmptyState
            title="Hozircha kategoriyalar yo'q"
            description="Boshlash uchun birinchi kategoriyangizni yarating."
            action={<Button size="sm" onClick={() => setModalCategory("new")}>Yangi kategoriya</Button>}
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Nomi</TableHead>
                <TableHead>Tavsif</TableHead>
                <TableHead>Holati</TableHead>
                <TableHead className="text-right" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {categories.map((category) => (
                <TableRow key={category.id}>
                  <TableCell className="font-medium">{category.name}</TableCell>
                  <TableCell className="text-muted-foreground">{category.description ?? "—"}</TableCell>
                  <TableCell>
                    <Badge variant={category.is_active ? "success" : "secondary"} dot>
                      {category.is_active ? "Faol" : "Nofaol"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => setModalCategory(category)} aria-label="Tahrirlash">
                        <Pencil className="size-4" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => setDeleteTarget(category)} aria-label="O'chirish">
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
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
          <FormField htmlFor="category-name" label="Nomi" required error={form.formState.errors.name?.message}>
            <Input id="category-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
          </FormField>
          <FormField htmlFor="category-description" label="Tavsif">
            <Input id="category-description" {...form.register("description")} />
          </FormField>
          <SwitchField
            control={form.control}
            name="is_active"
            htmlFor="category-active"
            label="Faol"
            description="Nofaol kategoriyalar yangi mahsulotlarda ko'rinmaydi."
          />
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

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { formatMoney } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { categoryService } from "@/services/category";
import { productService } from "@/services/product";
import { unitService, type UnitCreateInput } from "@/services/unit";
import type { Product } from "@/types/product";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";

const productFormSchema = z.object({
  name: z.string().min(1, "Nomi to'ldirilishi shart"),
  sku: z.string().min(1, "SKU to'ldirilishi shart"),
  barcode: z.string().optional(),
  category_id: z.string().min(1, "Kategoriyani tanlash shart"),
  unit_id: z.string().min(1, "Birlikni tanlash shart"),
  purchase_price: z.coerce.number({ invalid_type_error: "Tannarx raqam bo'lishi kerak" }).nonnegative("0 yoki undan katta bo'lishi kerak"),
  sale_price: z.coerce.number({ invalid_type_error: "Sotuv narxi raqam bo'lishi kerak" }).nonnegative("0 yoki undan katta bo'lishi kerak"),
  description: z.string().optional(),
  is_active: z.boolean(),
});
type ProductFormValues = z.infer<typeof productFormSchema>;

const unitFormSchema = z.object({
  name: z.string().min(1, "Nomi to'ldirilishi shart"),
  short_name: z.string().min(1, "Qisqartma to'ldirilishi shart"),
});
type UnitFormValues = z.infer<typeof unitFormSchema>;

type ModalState = "new" | Product | null;

export default function ProductsPage() {
  const { user } = useAuth();
  const isCeo = user?.role === "ceo" || user?.role == null;
  const queryClient = useQueryClient();
  const [modalProduct, setModalProduct] = React.useState<ModalState>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<Product | null>(null);
  const [isUnitModalOpen, setIsUnitModalOpen] = React.useState(false);

  const productsQuery = useQuery({ queryKey: ["products"], queryFn: productService.list });
  const categoriesQuery = useQuery({ queryKey: ["categories"], queryFn: categoryService.list });
  const unitsQuery = useQuery({ queryKey: ["units"], queryFn: unitService.list });

  const categoryOptions = React.useMemo(
    () => (categoriesQuery.data ?? []).map((c) => ({ label: c.name, value: String(c.id) })),
    [categoriesQuery.data]
  );
  const unitOptions = React.useMemo(
    () => (unitsQuery.data ?? []).map((u) => ({ label: u.name, value: String(u.id) })),
    [unitsQuery.data]
  );

  const form = useForm<ProductFormValues>({
    resolver: zodResolver(productFormSchema),
    defaultValues: {
      name: "",
      sku: "",
      barcode: "",
      category_id: "",
      unit_id: "",
      purchase_price: 0,
      sale_price: 0,
      description: "",
      is_active: true,
    },
  });

  React.useEffect(() => {
    if (modalProduct && modalProduct !== "new") {
      form.reset({
        name: modalProduct.name,
        sku: modalProduct.sku,
        barcode: modalProduct.barcode ?? "",
        category_id: String(modalProduct.category_id),
        unit_id: String(modalProduct.unit_id),
        purchase_price: Number(modalProduct.purchase_price),
        sale_price: Number(modalProduct.sale_price),
        description: modalProduct.description ?? "",
        is_active: modalProduct.is_active,
      });
    } else if (modalProduct === "new") {
      form.reset({
        name: "",
        sku: "",
        barcode: "",
        category_id: "",
        unit_id: "",
        purchase_price: 0,
        sale_price: 0,
        description: "",
        is_active: true,
      });
    }
  }, [modalProduct, form]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["products"] });

  const createMutation = useMutation({
    mutationFn: productService.create,
    onSuccess: () => {
      toast.success("Mahsulot yaratildi.");
      setModalProduct(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: ProductFormValues }) => productService.update(id, values),
    onSuccess: () => {
      toast.success("Mahsulot yangilandi.");
      setModalProduct(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const deleteMutation = useMutation({
    mutationFn: productService.remove,
    onSuccess: () => {
      toast.success("Mahsulot o'chirildi.");
      setDeleteTarget(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const unitForm = useForm<UnitFormValues>({
    resolver: zodResolver(unitFormSchema),
    defaultValues: { name: "", short_name: "" },
  });

  const createUnitMutation = useMutation({
    mutationFn: (values: UnitCreateInput) => unitService.create(values),
    onSuccess: async (unit) => {
      toast.success("Birlik yaratildi.");
      unitForm.reset({ name: "", short_name: "" });
      setIsUnitModalOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["units"] });
      form.setValue("unit_id", String(unit.id));
    },
    onError: toastMutationError,
  });

  const onSubmit = (values: ProductFormValues) => {
    if (modalProduct === "new") createMutation.mutate(values);
    else if (modalProduct) updateMutation.mutate({ id: modalProduct.id, values });
  };

  const isEditing = modalProduct !== null;
  const isError = productsQuery.isError || categoriesQuery.isError || unitsQuery.isError;
  const firstError = productsQuery.error ?? categoriesQuery.error ?? unitsQuery.error;
  const isLoading = productsQuery.isLoading || categoriesQuery.isLoading || unitsQuery.isLoading;
  const products = productsQuery.data ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Mahsulotlar"
        description={isCeo ? "Kompaniyangizning mahsulot katalogini boshqaring." : "Kompaniyangiz katalogidagi mahsulotlar."}
        actions={
          isCeo ? (
            <Button onClick={() => setModalProduct("new")}>
              <Plus />
              Yangi mahsulot
            </Button>
          ) : null
        }
      />

      <TableCard className="mt-6">
        {isError ? (
          <ErrorState
            error={firstError}
            onRetry={() => {
              void productsQuery.refetch();
              void categoriesQuery.refetch();
              void unitsQuery.refetch();
            }}
          />
        ) : isLoading ? (
          <TableSkeleton />
        ) : products.length === 0 ? (
          <EmptyState
            title="Hozircha mahsulotlar yo'q"
            description={isCeo ? "Boshlash uchun birinchi mahsulotingizni qo'shing." : "Mahsulotlar topilmadi."}
            action={isCeo ? <Button size="sm" onClick={() => setModalProduct("new")}>Yangi mahsulot</Button> : undefined}
          />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Nomi</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead>Kategoriya</TableHead>
                  <TableHead>Birlik</TableHead>
                  <TableHead className="text-right">Sotuv narxi</TableHead>
                  <TableHead>Holati</TableHead>
                  {isCeo ? <TableHead className="text-right" /> : null}
                </TableRow>
              </TableHeader>
              <TableBody>
                {products.map((product) => (
                  <TableRow key={product.id}>
                    <TableCell className="font-medium">{product.name}</TableCell>
                    <TableCell className="text-muted-foreground">{product.sku}</TableCell>
                    <TableCell className="text-muted-foreground">{product.category?.name ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{product.unit?.short_name ?? "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatMoney(product.sale_price)}</TableCell>
                    <TableCell>
                      <Badge variant={product.is_active ? "success" : "secondary"} dot>
                        {product.is_active ? "Faol" : "Nofaol"}
                      </Badge>
                    </TableCell>
                    {isCeo ? (
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1.5">
                          <Button variant="ghost" size="icon-sm" onClick={() => setModalProduct(product)} aria-label="Tahrirlash">
                            <Pencil className="size-4" />
                          </Button>
                          <Button variant="ghost" size="icon-sm" onClick={() => setDeleteTarget(product)} aria-label="O'chirish">
                            <Trash2 className="size-4" />
                          </Button>
                        </div>
                      </TableCell>
                    ) : null}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </TableCard>

      <Modal
        open={isEditing}
        onOpenChange={(open) => !open && setModalProduct(null)}
        title={modalProduct === "new" ? "Yangi mahsulot" : "Mahsulotni tahrirlash"}
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setModalProduct(null)}>
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
            <FormField htmlFor="product-name" label="Nomi" required error={form.formState.errors.name?.message}>
              <Input id="product-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
            </FormField>
            <FormField htmlFor="product-sku" label="SKU" required error={form.formState.errors.sku?.message}>
              <Input id="product-sku" invalid={!!form.formState.errors.sku} {...form.register("sku")} />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField htmlFor="product-category" label="Kategoriya" required error={form.formState.errors.category_id?.message}>
              <Select
                id="product-category"
                placeholder="Kategoriyani tanlang…"
                options={categoryOptions}
                invalid={!!form.formState.errors.category_id}
                {...form.register("category_id")}
              />
            </FormField>
            <FormField htmlFor="product-unit" label="Birlik" required error={form.formState.errors.unit_id?.message}>
              <div className="flex gap-2">
                <Select
                  id="product-unit"
                  placeholder="Birlikni tanlang…"
                  options={unitOptions}
                  invalid={!!form.formState.errors.unit_id}
                  className="flex-1"
                  {...form.register("unit_id")}
                />
                <Button type="button" variant="outline" size="icon" onClick={() => setIsUnitModalOpen(true)} aria-label="Yangi birlik">
                  <Plus className="size-4" />
                </Button>
              </div>
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField htmlFor="product-purchase-price" label="Tannarx">
              <Input id="product-purchase-price" type="number" step="0.01" {...form.register("purchase_price")} />
            </FormField>
            <FormField htmlFor="product-sale-price" label="Sotuv narxi">
              <Input id="product-sale-price" type="number" step="0.01" {...form.register("sale_price")} />
            </FormField>
          </div>
          <FormField htmlFor="product-barcode" label="Shtrix-kod">
            <Input id="product-barcode" {...form.register("barcode")} />
          </FormField>
          <FormField htmlFor="product-description" label="Tavsif">
            <Input id="product-description" {...form.register("description")} />
          </FormField>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`${deleteTarget?.name} o'chirilsinmi?`}
        description="Ushbu mahsulot katalogdan o'chiriladi."
        confirmLabel="O'chirish"
        variant="destructive"
        loading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />

      <Modal
        open={isUnitModalOpen}
        onOpenChange={(open) => !open && setIsUnitModalOpen(false)}
        title="Yangi birlik"
        footer={
          <>
            <Button variant="outline" onClick={() => setIsUnitModalOpen(false)}>
              Bekor qilish
            </Button>
            <Button onClick={unitForm.handleSubmit((v) => createUnitMutation.mutate(v))} loading={createUnitMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={unitForm.handleSubmit((v) => createUnitMutation.mutate(v))}>
          <FormField htmlFor="unit-name" label="Nomi" required error={unitForm.formState.errors.name?.message}>
            <Input id="unit-name" placeholder="Kilogramm" invalid={!!unitForm.formState.errors.name} {...unitForm.register("name")} />
          </FormField>
          <FormField htmlFor="unit-short-name" label="Qisqartma" required error={unitForm.formState.errors.short_name?.message}>
            <Input id="unit-short-name" placeholder="kg" invalid={!!unitForm.formState.errors.short_name} {...unitForm.register("short_name")} />
          </FormField>
        </form>
      </Modal>
    </ContentContainer>
  );
}

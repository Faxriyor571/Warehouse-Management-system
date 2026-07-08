import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { getErrorMessage } from "@/lib/http";
import { formatMoney } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { categoryService } from "@/services/category";
import { productService } from "@/services/product";
import { unitService } from "@/services/unit";
import type { Product } from "@/types/product";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";

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

type ModalState = "new" | Product | null;

export default function ProductsPage() {
  const { user } = useAuth();
  const isCeo = user?.role === "ceo" || user?.role == null;
  const queryClient = useQueryClient();
  const [modalProduct, setModalProduct] = React.useState<ModalState>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<Product | null>(null);

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
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: ProductFormValues }) => productService.update(id, values),
    onSuccess: () => {
      toast.success("Mahsulot yangilandi.");
      setModalProduct(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: productService.remove,
    onSuccess: () => {
      toast.success("Mahsulot o'chirildi.");
      setDeleteTarget(null);
      void invalidate();
    },
    onError: (error: unknown) => toast.error(getErrorMessage(error)),
  });

  const onSubmit = (values: ProductFormValues) => {
    if (modalProduct === "new") createMutation.mutate(values);
    else if (modalProduct) updateMutation.mutate({ id: modalProduct.id, values });
  };

  const isEditing = modalProduct !== null;
  const isError = productsQuery.isError || categoriesQuery.isError || unitsQuery.isError;
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

      <div className="mt-6 overflow-hidden rounded-lg border">
        {isError ? (
          <ErrorState
            onRetry={() => {
              void productsQuery.refetch();
              void categoriesQuery.refetch();
              void unitsQuery.refetch();
            }}
          />
        ) : isLoading ? (
          <div className="space-y-3 p-6">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : products.length === 0 ? (
          <EmptyState
            title="Hozircha mahsulotlar yo'q"
            description={isCeo ? "Boshlash uchun birinchi mahsulotingizni qo'shing." : "Mahsulotlar topilmadi."}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-6 py-2 text-left font-medium">Nomi</th>
                  <th className="px-6 py-2 text-left font-medium">SKU</th>
                  <th className="px-6 py-2 text-left font-medium">Kategoriya</th>
                  <th className="px-6 py-2 text-left font-medium">Birlik</th>
                  <th className="px-6 py-2 text-right font-medium">Sotuv narxi</th>
                  <th className="px-6 py-2 text-left font-medium">Holati</th>
                  {isCeo ? <th className="px-6 py-2 text-right font-medium" /> : null}
                </tr>
              </thead>
              <tbody className="divide-y">
                {products.map((product) => (
                  <tr key={product.id}>
                    <td className="px-6 py-2.5 font-medium">{product.name}</td>
                    <td className="px-6 py-2.5 text-muted-foreground">{product.sku}</td>
                    <td className="px-6 py-2.5 text-muted-foreground">{product.category?.name ?? "—"}</td>
                    <td className="px-6 py-2.5 text-muted-foreground">{product.unit?.short_name ?? "—"}</td>
                    <td className="px-6 py-2.5 text-right tabular-nums">{formatMoney(product.sale_price)}</td>
                    <td className="px-6 py-2.5">
                      <Badge variant={product.is_active ? "success" : "secondary"} dot>
                        {product.is_active ? "Faol" : "Nofaol"}
                      </Badge>
                    </td>
                    {isCeo ? (
                      <td className="px-6 py-2.5">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon-sm" onClick={() => setModalProduct(product)} aria-label="Tahrirlash">
                            <Pencil className="size-4" />
                          </Button>
                          <Button variant="ghost" size="icon-sm" onClick={() => setDeleteTarget(product)} aria-label="O'chirish">
                            <Trash2 className="size-4" />
                          </Button>
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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
            <div className="space-y-2">
              <Label htmlFor="product-name" required>
                Nomi
              </Label>
              <Input id="product-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
              {form.formState.errors.name ? <p className="text-sm text-destructive">{form.formState.errors.name.message}</p> : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="product-sku" required>
                SKU
              </Label>
              <Input id="product-sku" invalid={!!form.formState.errors.sku} {...form.register("sku")} />
              {form.formState.errors.sku ? <p className="text-sm text-destructive">{form.formState.errors.sku.message}</p> : null}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="product-category" required>
                Kategoriya
              </Label>
              <Select
                id="product-category"
                placeholder="Kategoriyani tanlang…"
                options={categoryOptions}
                invalid={!!form.formState.errors.category_id}
                {...form.register("category_id")}
              />
              {form.formState.errors.category_id ? (
                <p className="text-sm text-destructive">{form.formState.errors.category_id.message}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="product-unit" required>
                Birlik
              </Label>
              <Select
                id="product-unit"
                placeholder="Birlikni tanlang…"
                options={unitOptions}
                invalid={!!form.formState.errors.unit_id}
                {...form.register("unit_id")}
              />
              {form.formState.errors.unit_id ? (
                <p className="text-sm text-destructive">{form.formState.errors.unit_id.message}</p>
              ) : null}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="product-purchase-price">Tannarx</Label>
              <Input id="product-purchase-price" type="number" step="0.01" {...form.register("purchase_price")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="product-sale-price">Sotuv narxi</Label>
              <Input id="product-sale-price" type="number" step="0.01" {...form.register("sale_price")} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="product-barcode">Shtrix-kod</Label>
            <Input id="product-barcode" {...form.register("barcode")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="product-description">Tavsif</Label>
            <Input id="product-description" {...form.register("description")} />
          </div>
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
    </ContentContainer>
  );
}

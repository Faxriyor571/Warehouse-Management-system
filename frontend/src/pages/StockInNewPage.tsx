import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useFieldArray, useForm } from "react-hook-form";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { formatMoney, nowForDatetimeLocalInput } from "@/lib/formatters";
import { isCompanyWide } from "@/lib/permissions";
import { useAuth } from "@/providers/auth-provider";
import { productService } from "@/services/product";
import { stockInService } from "@/services/stock-in";
import { storeService } from "@/services/store";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { FormField } from "@/components/forms/form-field";

const lineItemSchema = z.object({
  product_id: z.string().min(1, "Mahsulotni tanlash shart"),
  quantity: z.coerce.number({ invalid_type_error: "Miqdor raqam bo'lishi kerak" }).positive("0 dan katta bo'lishi kerak"),
  price: z.coerce.number({ invalid_type_error: "Narx raqam bo'lishi kerak" }).nonnegative("0 yoki undan katta bo'lishi kerak"),
});

const stockInFormSchema = z.object({
  store_id: z.string().optional(),
  date: z.string().optional(),
  note: z.string().optional(),
  items: z.array(lineItemSchema).min(1, "Kamida bitta qator qo'shing"),
});
type StockInFormValues = z.infer<typeof stockInFormSchema>;

export default function StockInNewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  // A company-wide identity (Warehouse Employee in practice — the only one
  // who can actually submit this form) must supply store_id explicitly
  // (backend's resolve_scope); the legacy single-tenant admin (role === null)
  // resolves to (None, None) and never needs a store.
  const isCeo = isCompanyWide(user);
  const queryClient = useQueryClient();

  const form = useForm<StockInFormValues>({
    resolver: zodResolver(stockInFormSchema),
    defaultValues: { store_id: "", date: nowForDatetimeLocalInput(), note: "", items: [{ product_id: "", quantity: 1, price: 0 }] },
  });

  const { fields, append, remove } = useFieldArray({ control: form.control, name: "items" });
  const watchedItems = form.watch("items");

  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });
  const productsQuery = useQuery({ queryKey: ["products"], queryFn: productService.list });

  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
  );
  const productOptions = React.useMemo(
    () => (productsQuery.data ?? []).map((p) => ({ label: `${p.name} (${p.sku})`, value: String(p.id) })),
    [productsQuery.data]
  );

  const createMutation = useMutation({
    mutationFn: stockInService.create,
    onSuccess: (created) => {
      toast.success(`${created.reference} raqamli kirim hujjati yaratildi.`);
      void queryClient.invalidateQueries({ queryKey: ["stock-in"] });
      navigate(`/stock-in/${created.id}`);
    },
    onError: toastMutationError,
  });

  const onSubmit = (values: StockInFormValues) => {
    if (isCeo && !values.store_id) {
      form.setError("store_id", { message: "Do'konni tanlash shart" });
      return;
    }
    createMutation.mutate(values);
  };

  const total = watchedItems.reduce((sum, item) => sum + (Number(item?.quantity) || 0) * (Number(item?.price) || 0), 0);

  return (
    <ContentContainer>
      <PageHeader title="Yangi kirim" description="Kirimni qayd eting. Saqlangach ombordagi qoldiq avtomatik oshadi." />

      <form className="mt-6 space-y-6" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {isCeo ? (
            <FormField htmlFor="stock-in-store" label="Do'kon" required error={form.formState.errors.store_id?.message}>
              <Select id="stock-in-store" options={storeOptions} placeholder="Do'konni tanlang…" invalid={!!form.formState.errors.store_id} {...form.register("store_id")} />
            </FormField>
          ) : null}
          <FormField htmlFor="stock-in-date" label="Sana">
            <Input id="stock-in-date" type="datetime-local" {...form.register("date")} />
          </FormField>
        </div>

        <FormField htmlFor="stock-in-note" label="Izoh">
          <Input id="stock-in-note" {...form.register("note")} />
        </FormField>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-foreground">Qatorlar</h2>
            <Button type="button" variant="outline" size="sm" onClick={() => append({ product_id: "", quantity: 1, price: 0 })}>
              <Plus />
              Boshqa mahsulot qo'shish
            </Button>
          </div>

          {form.formState.errors.items?.root ? (
            <p className="text-sm text-destructive">{form.formState.errors.items.root.message}</p>
          ) : null}

          <div className="space-y-3">
            {fields.map((field, index) => {
              const line = watchedItems[index];
              const subtotal = (Number(line?.quantity) || 0) * (Number(line?.price) || 0);
              return (
                <div key={field.id} className="grid grid-cols-1 items-end gap-3 rounded-xl border border-border/70 bg-card p-4 shadow-xs transition-colors hover:border-primary/30 sm:grid-cols-[2fr_1fr_1fr_1fr_auto]">
                  <FormField htmlFor={`item-product-${index}`} label="Mahsulot" required>
                    <Select id={`item-product-${index}`} options={productOptions} placeholder="Mahsulotni tanlang…" {...form.register(`items.${index}.product_id`)} />
                  </FormField>
                  <FormField htmlFor={`item-quantity-${index}`} label="Miqdor" required>
                    <Input id={`item-quantity-${index}`} type="number" step="0.001" {...form.register(`items.${index}.quantity`)} />
                  </FormField>
                  <FormField htmlFor={`item-price-${index}`} label="Narx" required>
                    <Input id={`item-price-${index}`} type="number" step="0.01" {...form.register(`items.${index}.price`)} />
                  </FormField>
                  <div className="space-y-2">
                    <span className="text-sm font-medium text-foreground">Oraliq summa</span>
                    <p className="tabular-nums text-sm text-muted-foreground">{formatMoney(subtotal)}</p>
                  </div>
                  <Button type="button" variant="ghost" size="icon-sm" disabled={fields.length === 1} onClick={() => remove(index)} aria-label="Qatorni o'chirish">
                    <Trash2 />
                  </Button>
                </div>
              );
            })}
          </div>

          <div className="flex justify-end border-t border-border/70 pt-4">
            <p className="text-sm">
              <span className="text-muted-foreground">Jami: </span>
              <span className="font-medium tabular-nums">{formatMoney(total)}</span>
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => navigate("/stock-in")}>
            Bekor qilish
          </Button>
          <Button type="submit" loading={createMutation.isPending}>
            Saqlash
          </Button>
        </div>
      </form>
    </ContentContainer>
  );
}

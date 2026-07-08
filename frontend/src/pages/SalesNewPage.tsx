import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useFieldArray, useForm } from "react-hook-form";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { formatMoney } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { customerService } from "@/services/customer";
import { paymentMethodService } from "@/services/payment-method";
import { productService } from "@/services/product";
import { saleService } from "@/services/sale";
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
  // Blank means "use the product's current sale price" — must resolve to
  // undefined, not 0, or the backend treats it as an explicit price override
  // (only allowed for legal-entity customers).
  price: z.preprocess(
    (val) => (val === "" || val === undefined || val === null ? undefined : val),
    z.coerce.number({ invalid_type_error: "Narx raqam bo'lishi kerak" }).nonnegative().optional()
  ),
  discount: z.coerce.number({ invalid_type_error: "Chegirma raqam bo'lishi kerak" }).nonnegative("0 yoki undan katta bo'lishi kerak"),
});

const paymentLineSchema = z.object({
  payment_method_id: z.string().optional().default(""),
  amount: z.coerce.number({ invalid_type_error: "Summasi raqam bo'lishi kerak" }).nonnegative("0 yoki undan katta bo'lishi kerak"),
  note: z.string().optional(),
});

const saleFormSchema = z.object({
  store_id: z.string().optional(),
  customer_id: z.string().optional(),
  date: z.string().optional(),
  discount: z.coerce.number({ invalid_type_error: "Chegirma raqam bo'lishi kerak" }).nonnegative("0 yoki undan katta bo'lishi kerak"),
  note: z.string().optional(),
  due_date: z.string().optional(),
  items: z.array(lineItemSchema).min(1, "Kamida bitta qator qo'shing"),
  payments: z.array(paymentLineSchema),
});
type SaleFormSchemaValues = z.infer<typeof saleFormSchema>;

export default function SalesNewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  // Only an actual CEO must supply store_id; the legacy single-tenant admin
  // resolves to (None, None) and never needs a store (see Stock In).
  const isCeo = user?.role === "ceo";
  const queryClient = useQueryClient();

  const form = useForm<SaleFormSchemaValues>({
    resolver: zodResolver(saleFormSchema),
    defaultValues: {
      store_id: "",
      customer_id: "",
      date: "",
      discount: 0,
      note: "",
      due_date: "",
      items: [{ product_id: "", quantity: 1, price: undefined, discount: 0 }],
      payments: [],
    },
  });

  const itemsArray = useFieldArray({ control: form.control, name: "items" });
  const paymentsArray = useFieldArray({ control: form.control, name: "payments" });
  const watchedItems = form.watch("items");
  const watchedPayments = form.watch("payments");
  const watchedDiscount = form.watch("discount");

  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });
  const customersQuery = useQuery({ queryKey: ["customers"], queryFn: customerService.list });
  const productsQuery = useQuery({ queryKey: ["products"], queryFn: productService.list });
  const paymentMethodsQuery = useQuery({ queryKey: ["payment-methods"], queryFn: paymentMethodService.list });

  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
  );
  const customerOptions = React.useMemo(
    () => (customersQuery.data ?? []).map((c) => ({ label: c.full_name, value: String(c.id) })),
    [customersQuery.data]
  );
  const productOptions = React.useMemo(
    () => (productsQuery.data ?? []).map((p) => ({ label: `${p.name} (${p.sku})`, value: String(p.id) })),
    [productsQuery.data]
  );
  const paymentMethodOptions = React.useMemo(
    () => (paymentMethodsQuery.data ?? []).filter((m) => m.is_active).map((m) => ({ label: m.name, value: String(m.id) })),
    [paymentMethodsQuery.data]
  );

  const createMutation = useMutation({
    mutationFn: saleService.create,
    onSuccess: (created) => {
      toast.success(`${created.reference} raqamli savdo hujjati yaratildi.`);
      void queryClient.invalidateQueries({ queryKey: ["sales"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/sales/${created.id}`);
    },
    onError: toastMutationError,
  });

  const onSubmit = (values: SaleFormSchemaValues) => {
    if (isCeo && !values.store_id) {
      form.setError("store_id", { message: "Do'konni tanlash shart" });
      return;
    }
    createMutation.mutate(values);
  };

  const itemsSubtotal = watchedItems.reduce((sum, item) => {
    const qty = Number(item?.quantity) || 0;
    const price = Number(item?.price) || 0;
    const discount = Number(item?.discount) || 0;
    return sum + (qty * price - discount);
  }, 0);
  const total = Math.max(itemsSubtotal - (Number(watchedDiscount) || 0), 0);
  const paidTotal = watchedPayments.reduce((sum, p) => sum + (Number(p?.amount) || 0), 0);

  return (
    <ContentContainer>
      <PageHeader title="Yangi savdo" description="Savdoni qayd eting. Saqlangach ombordagi qoldiq avtomatik kamayadi." />

      <form className="mt-6 space-y-6" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {isCeo ? (
            <FormField htmlFor="sale-store" label="Do'kon" required error={form.formState.errors.store_id?.message}>
              <Select id="sale-store" options={storeOptions} placeholder="Do'konni tanlang…" invalid={!!form.formState.errors.store_id} {...form.register("store_id")} />
            </FormField>
          ) : null}
          <FormField htmlFor="sale-customer" label="Mijoz">
            <Select id="sale-customer" options={customerOptions} placeholder="Mijozni tanlang…" {...form.register("customer_id")} />
          </FormField>
          <FormField htmlFor="sale-date" label="Sana">
            <Input id="sale-date" type="datetime-local" {...form.register("date")} />
          </FormField>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField htmlFor="sale-discount" label="Hujjat chegirmasi">
            <Input id="sale-discount" type="number" step="0.01" {...form.register("discount")} />
          </FormField>
          <FormField htmlFor="sale-due-date" label="Qarz muddati">
            <Input id="sale-due-date" type="date" {...form.register("due_date")} />
          </FormField>
          <FormField htmlFor="sale-note" label="Izoh">
            <Input id="sale-note" {...form.register("note")} />
          </FormField>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-foreground">Qatorlar</h2>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => itemsArray.append({ product_id: "", quantity: 1, price: undefined, discount: 0 })}
            >
              <Plus />
              Qator qo'shish
            </Button>
          </div>

          {form.formState.errors.items?.root ? (
            <p className="text-sm text-destructive">{form.formState.errors.items.root.message}</p>
          ) : null}

          <div className="space-y-3">
            {itemsArray.fields.map((field, index) => {
              const line = watchedItems[index];
              const qty = Number(line?.quantity) || 0;
              const price = Number(line?.price) || 0;
              const discount = Number(line?.discount) || 0;
              const subtotal = qty * price - discount;
              return (
                <div key={field.id} className="grid grid-cols-1 items-end gap-3 rounded-xl border border-border/70 bg-card p-4 shadow-xs transition-colors hover:border-primary/30 sm:grid-cols-[2fr_1fr_1fr_1fr_1fr_auto]">
                  <FormField htmlFor={`sale-item-product-${index}`} label="Mahsulot" required>
                    <Select id={`sale-item-product-${index}`} options={productOptions} placeholder="Mahsulotni tanlang…" {...form.register(`items.${index}.product_id`)} />
                  </FormField>
                  <FormField htmlFor={`sale-item-quantity-${index}`} label="Miqdor" required>
                    <Input id={`sale-item-quantity-${index}`} type="number" step="0.001" {...form.register(`items.${index}.quantity`)} />
                  </FormField>
                  <FormField htmlFor={`sale-item-price-${index}`} label="Narx">
                    <Input id={`sale-item-price-${index}`} type="number" step="0.01" placeholder="Standart narx" {...form.register(`items.${index}.price`)} />
                  </FormField>
                  <FormField htmlFor={`sale-item-discount-${index}`} label="Chegirma">
                    <Input id={`sale-item-discount-${index}`} type="number" step="0.01" {...form.register(`items.${index}.discount`)} />
                  </FormField>
                  <div className="space-y-2">
                    <span className="text-sm font-medium text-foreground">Oraliq summa</span>
                    <p className="tabular-nums text-sm text-muted-foreground">{formatMoney(subtotal)}</p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    disabled={itemsArray.fields.length === 1}
                    onClick={() => itemsArray.remove(index)}
                    aria-label="Qatorni o'chirish"
                  >
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

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-foreground">To'lovlar</h2>
            <Button type="button" variant="outline" size="sm" onClick={() => paymentsArray.append({ payment_method_id: "", amount: 0, note: "" })}>
              <Plus />
              To'lov qo'shish
            </Button>
          </div>

          {paymentsArray.fields.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              To'lov qo'shilmasa, jami summa mijoz qarziga yoziladi.
            </p>
          ) : (
            <div className="space-y-3">
              {paymentsArray.fields.map((field, index) => (
                <div key={field.id} className="grid grid-cols-1 items-end gap-3 rounded-xl border border-border/70 bg-card p-4 shadow-xs transition-colors hover:border-primary/30 sm:grid-cols-[1fr_1fr_2fr_auto]">
                  <FormField htmlFor={`sale-payment-method-${index}`} label="To'lov turi" required>
                    <Select id={`sale-payment-method-${index}`} options={paymentMethodOptions} placeholder="Tanlang…" {...form.register(`payments.${index}.payment_method_id`)} />
                  </FormField>
                  <FormField htmlFor={`sale-payment-amount-${index}`} label="Summasi" required>
                    <Input id={`sale-payment-amount-${index}`} type="number" step="0.01" {...form.register(`payments.${index}.amount`)} />
                  </FormField>
                  <FormField htmlFor={`sale-payment-note-${index}`} label="Izoh">
                    <Input id={`sale-payment-note-${index}`} {...form.register(`payments.${index}.note`)} />
                  </FormField>
                  <Button type="button" variant="ghost" size="icon-sm" onClick={() => paymentsArray.remove(index)} aria-label="To'lovni o'chirish">
                    <Trash2 />
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end gap-6 border-t border-border/70 pt-4 text-sm">
            <p>
              <span className="text-muted-foreground">To'langan: </span>
              <span className="font-medium tabular-nums">{formatMoney(paidTotal)}</span>
            </p>
            <p>
              <span className="text-muted-foreground">Qarzga qoladi: </span>
              <span className="font-medium tabular-nums">{formatMoney(Math.max(total - paidTotal, 0))}</span>
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => navigate("/sales")}>
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

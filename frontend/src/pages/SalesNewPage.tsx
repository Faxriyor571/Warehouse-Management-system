import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useFieldArray, useForm } from "react-hook-form";
import { AlertTriangle, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { formatMoney, nowForDatetimeLocalInput } from "@/lib/formatters";
import { isCompanyWide } from "@/lib/permissions";
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

const customerTypeOptions = [
  { label: "Jismoniy shaxs", value: "individual" },
  { label: "Yuridik shaxs (Kompaniya)", value: "legal_entity" },
];

// An item left without an explicit price uses the product's current sale
// price (see lineItemSchema's price comment) — so "what will this line
// actually cost" needs the product catalog, not just what's typed in the
// price box, or a plain (very common) no-override line would be priced at 0
// and the debt section below would never trigger. `price` here is the raw
// react-hook-form watch() value, which is "" (not undefined) for a cleared
// number input — unlike the Zod schema's preprocessed value — so both must
// be treated as "no override".
function effectivePrice(price: number | string | undefined, productId: string | undefined, priceByProductId: Record<string, number>): number {
  if (price !== undefined && price !== null && price !== "") return Number(price) || 0;
  return priceByProductId[productId ?? ""] ?? 0;
}

// Debt-owner fields are only meaningful once the sale actually leaves a
// remaining balance — computed the same way as the on-screen "Qarzga
// qoladi" total (items - discount - payments), then re-derived here since
// superRefine only sees raw form values, not component state.
function computeRemaining(
  data: { items: { product_id?: string; quantity: number; price?: number; discount: number }[]; discount: number; payments: { amount: number }[] },
  priceByProductId: Record<string, number>
) {
  const itemsSubtotal = data.items.reduce((sum, item) => {
    const qty = Number(item?.quantity) || 0;
    const price = effectivePrice(item?.price, item?.product_id, priceByProductId);
    const discount = Number(item?.discount) || 0;
    return sum + (qty * price - discount);
  }, 0);
  const total = Math.max(itemsSubtotal - (Number(data.discount) || 0), 0);
  const paidTotal = data.payments.reduce((sum, p) => sum + (Number(p?.amount) || 0), 0);
  return Math.max(total - paidTotal, 0);
}

function buildSaleFormSchema(priceByProductId: Record<string, number>) {
  return z
    .object({
      store_id: z.string().optional(),
      customer_type: z.enum(["individual", "legal_entity"]),
      customer_id: z.string().optional(),
      debtor_full_name: z.string().optional(),
      debtor_phone: z.string().optional(),
      debtor_company_name: z.string().optional(),
      date: z.string().optional(),
      discount: z.coerce.number({ invalid_type_error: "Chegirma raqam bo'lishi kerak" }).nonnegative("0 yoki undan katta bo'lishi kerak"),
      note: z.string().optional(),
      due_date: z.string().optional(),
      items: z.array(lineItemSchema).min(1, "Kamida bitta qator qo'shing"),
      payments: z.array(paymentLineSchema),
    })
    .superRefine((data, ctx) => {
      // No remaining debt: no customer information is required at all — the
      // sale can be completed immediately (business rule, see SalesNewPage
      // debt-driven UX).
      if (computeRemaining(data, priceByProductId) <= 0) return;

      if (data.customer_type === "individual") {
        if (!data.debtor_full_name || data.debtor_full_name.trim().length < 2) {
          ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["debtor_full_name"], message: "F.I.Sh. kamida 2 belgidan iborat bo'lishi kerak" });
        }
        if (!data.debtor_phone || data.debtor_phone.trim().length < 5) {
          ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["debtor_phone"], message: "Telefon raqami kiritilishi shart" });
        }
      } else if (!data.debtor_company_name || data.debtor_company_name.trim().length < 2) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["debtor_company_name"],
          message: "Kompaniya nomi kamida 2 belgidan iborat bo'lishi kerak",
        });
      }
    });
}
type SaleFormSchemaValues = z.infer<ReturnType<typeof buildSaleFormSchema>>;

export default function SalesNewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  // A company-wide identity must supply store_id explicitly; the legacy
  // single-tenant admin resolves to (None, None) and never needs a store
  // (see Stock In). In practice only a Cashier submits this form (store-
  // confined, so this rarely applies) — kept for defensive correctness.
  const isCeo = isCompanyWide(user);
  const queryClient = useQueryClient();

  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list, enabled: isCeo });
  const customersQuery = useQuery({ queryKey: ["customers"], queryFn: customerService.list });
  const productsQuery = useQuery({ queryKey: ["products"], queryFn: productService.list });
  const paymentMethodsQuery = useQuery({ queryKey: ["payment-methods"], queryFn: paymentMethodService.list });

  const productPriceById = React.useMemo(() => {
    const map: Record<string, number> = {};
    for (const p of productsQuery.data ?? []) map[String(p.id)] = Number(p.sale_price);
    return map;
  }, [productsQuery.data]);
  const saleFormSchema = React.useMemo(() => buildSaleFormSchema(productPriceById), [productPriceById]);

  const form = useForm<SaleFormSchemaValues>({
    resolver: zodResolver(saleFormSchema),
    defaultValues: {
      store_id: "",
      customer_type: "legal_entity",
      customer_id: "",
      debtor_full_name: "",
      debtor_phone: "",
      debtor_company_name: "",
      date: nowForDatetimeLocalInput(),
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
  const watchedCustomerType = form.watch("customer_type");

  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
  );
  // There's no standalone Customers management page anymore — a Company
  // debt owner is typed as plain text and resolved at submit time: reuse an
  // existing legal-entity customer if the name matches one exactly
  // (case-insensitive), otherwise create a new one inline, exactly like an
  // Individual debtor already does. The name list backs a <datalist> on the
  // input so repeat customers show up as a suggestion instead of risking a
  // near-duplicate record from a typo.
  const legalEntityCustomerNames = React.useMemo(
    () => (customersQuery.data ?? []).filter((c) => c.customer_type === "legal_entity").map((c) => c.full_name),
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

  const itemsSubtotal = watchedItems.reduce((sum, item) => {
    const qty = Number(item?.quantity) || 0;
    const price = effectivePrice(item?.price, item?.product_id, productPriceById);
    const discount = Number(item?.discount) || 0;
    return sum + (qty * price - discount);
  }, 0);
  const total = Math.max(itemsSubtotal - (Number(watchedDiscount) || 0), 0);
  const paidTotal = watchedPayments.reduce((sum, p) => sum + (Number(p?.amount) || 0), 0);
  const remainingDebt = Math.max(total - paidTotal, 0);
  const showDebtSection = remainingDebt > 0;

  const createMutation = useMutation({
    mutationFn: saleService.create,
    onSuccess: (created) => {
      toast.success(`${created.reference} raqamli savdo hujjati yaratildi.`);
      void queryClient.invalidateQueries({ queryKey: ["sales"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      // A sale with a remaining balance creates a debt as a side effect —
      // make sure the Debts page and every report reading debt data (both
      // Dashboard's alert banner and Debts' own summary stats) refetch
      // fresh rather than relying solely on staleTime:0 + unmount-on-
      // navigate to eventually catch up.
      void queryClient.invalidateQueries({ queryKey: ["debts"] });
      void queryClient.invalidateQueries({ queryKey: ["reports"] });
      navigate(`/sales/${created.id}`);
    },
    onError: toastMutationError,
  });

  // The individual+debt path awaits an inline customer-creation call before
  // createMutation.mutate() ever runs, so createMutation.isPending alone
  // leaves a window where the Save button looks idle and clickable — a fast
  // double-click there would create two customers and two sales. A ref-based
  // guard is required (not just the isProcessing state below): two clicks
  // fired synchronously both invoke onSubmit before React commits a
  // re-render, so both closures would still read a stale isProcessing=false
  // from state — a ref mutates immediately and is visible to the second
  // call right away. isProcessing itself only drives the visible loading UI.
  const isSubmittingRef = React.useRef(false);
  const [isProcessing, setIsProcessing] = React.useState(false);

  const onSubmit = async (values: SaleFormSchemaValues) => {
    if (isSubmittingRef.current) return;
    if (isCeo && !values.store_id) {
      form.setError("store_id", { message: "Do'konni tanlash shart" });
      return;
    }

    isSubmittingRef.current = true;
    setIsProcessing(true);
    try {
      // Fully paid: no debt owner needed, whatever was left over from a
      // previous customer-type toggle is discarded.
      if (remainingDebt <= 0) {
        createMutation.mutate({ ...values, customer_id: undefined });
        return;
      }

      // A debt will result. Neither debtor type is picked from a list —
      // there's no standalone Customers page to manage them ahead of time.
      if (values.customer_type === "individual") {
        const customer = await customerService.create({
          full_name: values.debtor_full_name,
          customer_type: "individual",
          phone: values.debtor_phone,
          is_active: true,
        });
        createMutation.mutate({ ...values, customer_id: String(customer.id) });
        return;
      }

      // Company: reuse an existing legal-entity customer with this exact
      // name (case-insensitive) if one exists, so repeat business
      // aggregates under one customer record instead of fragmenting across
      // a new one per sale; otherwise create it inline.
      const typedName = values.debtor_company_name?.trim() ?? "";
      const existing = (customersQuery.data ?? []).find(
        (c) => c.customer_type === "legal_entity" && c.full_name.trim().toLowerCase() === typedName.toLowerCase()
      );
      const company = existing ?? (await customerService.create({ full_name: typedName, customer_type: "legal_entity", is_active: true }));
      createMutation.mutate({ ...values, customer_id: String(company.id) });
    } catch (err) {
      toastMutationError(err);
    } finally {
      isSubmittingRef.current = false;
      setIsProcessing(false);
    }
  };

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
          <FormField htmlFor="sale-customer-type" label="Mijoz turi" required>
            <Select id="sale-customer-type" options={customerTypeOptions} {...form.register("customer_type")} />
          </FormField>
          <FormField htmlFor="sale-date" label="Sana">
            <Input id="sale-date" type="datetime-local" {...form.register("date")} />
          </FormField>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField htmlFor="sale-discount" label="Umumiy chegirma">
            <Input id="sale-discount" type="number" step="0.01" {...form.register("discount")} />
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
              Boshqa mahsulot qo'shish
            </Button>
          </div>

          {form.formState.errors.items?.root ? (
            <p className="text-sm text-destructive">{form.formState.errors.items.root.message}</p>
          ) : null}

          <div className="space-y-3">
            {itemsArray.fields.map((field, index) => {
              const line = watchedItems[index];
              const qty = Number(line?.quantity) || 0;
              const price = effectivePrice(line?.price, line?.product_id, productPriceById);
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

          {paymentsArray.fields.length > 0 ? (
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
          ) : null}

          <div className="flex justify-end gap-6 border-t border-border/70 pt-4 text-sm">
            <p>
              <span className="text-muted-foreground">To'langan: </span>
              <span className="font-medium tabular-nums">{formatMoney(paidTotal)}</span>
            </p>
            <p>
              <span className="text-muted-foreground">Qarzga qoladi: </span>
              <span className="font-medium tabular-nums">{formatMoney(remainingDebt)}</span>
            </p>
          </div>
        </div>

        {showDebtSection ? (
          <div className="space-y-4 rounded-xl border border-warning/40 bg-warning/5 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 size-5 shrink-0 text-warning" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground">Bu savdo qarz sifatida saqlanadi.</p>
                <p className="text-sm text-muted-foreground">
                  Qarzga qoladi: <span className="font-medium tabular-nums text-foreground">{formatMoney(remainingDebt)}</span>
                </p>
              </div>
            </div>

            {watchedCustomerType === "individual" ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  htmlFor="sale-debtor-name"
                  label="F.I.Sh."
                  required
                  error={form.formState.errors.debtor_full_name?.message}
                >
                  <Input
                    id="sale-debtor-name"
                    invalid={!!form.formState.errors.debtor_full_name}
                    {...form.register("debtor_full_name")}
                  />
                </FormField>
                <FormField
                  htmlFor="sale-debtor-phone"
                  label="Telefon"
                  required
                  error={form.formState.errors.debtor_phone?.message}
                >
                  <Input
                    id="sale-debtor-phone"
                    placeholder="+998901234567"
                    invalid={!!form.formState.errors.debtor_phone}
                    {...form.register("debtor_phone")}
                  />
                </FormField>
              </div>
            ) : (
              <FormField
                htmlFor="sale-debt-company"
                label="Kompaniya nomi"
                required
                error={form.formState.errors.debtor_company_name?.message}
              >
                <Input
                  id="sale-debt-company"
                  list="sale-debt-company-suggestions"
                  placeholder="Kompaniya nomini kiriting…"
                  invalid={!!form.formState.errors.debtor_company_name}
                  {...form.register("debtor_company_name")}
                />
                <datalist id="sale-debt-company-suggestions">
                  {legalEntityCustomerNames.map((name) => (
                    <option key={name} value={name} />
                  ))}
                </datalist>
              </FormField>
            )}

            <FormField htmlFor="sale-due-date" label="Qarz muddati">
              <Input id="sale-due-date" type="date" {...form.register("due_date")} />
            </FormField>
          </div>
        ) : null}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => navigate("/sales")}>
            Bekor qilish
          </Button>
          <Button type="submit" loading={isProcessing || createMutation.isPending}>
            Saqlash
          </Button>
        </div>
      </form>
    </ContentContainer>
  );
}

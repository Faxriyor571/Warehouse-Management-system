import { http } from "@/lib/http";
import type { PaginatedResponse } from "@/types/common";
import type {
  Sale,
  SaleFormValues,
  SaleListParams,
  SalesReturn,
  SalesReturnFormValues,
} from "@/types/sale";

export const saleService = {
  async list(params: SaleListParams): Promise<PaginatedResponse<Sale>> {
    const { data } = await http.get<PaginatedResponse<Sale>>("/sales", {
      params: { ...params, page_size: 20 },
    });
    return data;
  },

  async get(id: number): Promise<Sale> {
    const { data } = await http.get<Sale>(`/sales/${id}`);
    return data;
  },

  async create(values: SaleFormValues): Promise<Sale> {
    const { data } = await http.post<Sale>("/sales", {
      store_id: values.store_id ? Number(values.store_id) : undefined,
      customer_id: values.customer_id ? Number(values.customer_id) : null,
      date: values.date ? new Date(values.date).toISOString() : undefined,
      discount: values.discount,
      note: values.note || null,
      due_date: values.due_date || null,
      items: values.items.map((item) => ({
        product_id: Number(item.product_id),
        quantity: item.quantity,
        price: item.price,
        discount: item.discount,
      })),
      payments: values.payments
        .filter((p) => p.payment_method_id && p.amount > 0)
        .map((p) => ({
          payment_method_id: Number(p.payment_method_id),
          amount: p.amount,
          note: p.note || null,
        })),
    });
    return data;
  },

  async createReturn(saleId: number, values: SalesReturnFormValues): Promise<SalesReturn> {
    const { data } = await http.post<SalesReturn>(`/sales/${saleId}/returns`, values);
    return data;
  },

  async listReturns(saleId: number): Promise<SalesReturn[]> {
    const { data } = await http.get<SalesReturn[]>(`/sales/${saleId}/returns`);
    return data;
  },
};

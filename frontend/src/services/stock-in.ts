import { http } from "@/lib/http";
import type { PaginatedResponse } from "@/types/common";
import type { StockIn, StockInFormValues, StockInListParams } from "@/types/stock-in";

export const stockInService = {
  async list(params: StockInListParams): Promise<PaginatedResponse<StockIn>> {
    const { data } = await http.get<PaginatedResponse<StockIn>>("/stock-in", {
      params: { ...params, page_size: 20 },
    });
    return data;
  },

  async get(id: number): Promise<StockIn> {
    const { data } = await http.get<StockIn>(`/stock-in/${id}`);
    return data;
  },

  async create(values: StockInFormValues): Promise<StockIn> {
    const { data } = await http.post<StockIn>("/stock-in", {
      store_id: values.store_id ? Number(values.store_id) : undefined,
      date: values.date ? new Date(values.date).toISOString() : undefined,
      note: values.note || null,
      items: values.items.map((item) => ({
        product_id: Number(item.product_id),
        quantity: item.quantity,
        price: item.price,
      })),
    });
    return data;
  },
};

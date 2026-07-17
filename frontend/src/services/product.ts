import { http } from "@/lib/http";
import type { Product, ProductFormValues } from "@/types/product";
import type { PaginatedResponse } from "@/types/common";

export interface ProductPayload {
  name: string;
  sku: string;
  barcode: string | null;
  category_id: number;
  unit_id: number;
  purchase_price: number;
  sale_price: number;
  description: string | null;
  is_active: boolean;
}

function toPayload(values: ProductFormValues): ProductPayload {
  return {
    name: values.name,
    sku: values.sku,
    barcode: values.barcode || null,
    category_id: Number(values.category_id),
    unit_id: Number(values.unit_id),
    purchase_price: values.purchase_price,
    sale_price: values.sale_price,
    description: values.description || null,
    is_active: values.is_active,
  };
}

export const productService = {
  async list(): Promise<Product[]> {
    const { data } = await http.get<PaginatedResponse<Product>>("/products", {
      params: { page_size: 200 },
    });
    return data.items;
  },

  async create(values: ProductFormValues): Promise<Product> {
    const { data } = await http.post<Product>("/products", toPayload(values));
    return data;
  },

  async update(id: number, values: ProductFormValues): Promise<Product> {
    const { data } = await http.put<Product>(`/products/${id}`, toPayload(values));
    return data;
  },

  async remove(id: number): Promise<void> {
    await http.delete(`/products/${id}`);
  },
};

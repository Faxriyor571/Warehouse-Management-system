import { http } from "@/lib/http";
import type { Category, CategoryFormValues } from "@/types/category";
import type { PaginatedResponse } from "@/types/common";

function toPayload(values: CategoryFormValues) {
  return {
    name: values.name,
    description: values.description || null,
    is_active: values.is_active,
  };
}

export const categoryService = {
  async list(): Promise<Category[]> {
    const { data } = await http.get<PaginatedResponse<Category>>("/categories", {
      params: { page_size: 200 },
    });
    return data.items;
  },

  async create(values: CategoryFormValues): Promise<Category> {
    const { data } = await http.post<Category>("/categories", toPayload(values));
    return data;
  },

  async update(id: number, values: CategoryFormValues): Promise<Category> {
    const { data } = await http.put<Category>(`/categories/${id}`, toPayload(values));
    return data;
  },

  async remove(id: number): Promise<void> {
    await http.delete(`/categories/${id}`);
  },
};

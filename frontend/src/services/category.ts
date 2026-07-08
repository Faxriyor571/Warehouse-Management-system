import { http } from "@/lib/http";
import type { Category } from "@/types/category";
import type { PaginatedResponse } from "@/types/common";

export const categoryService = {
  async list(): Promise<Category[]> {
    const { data } = await http.get<PaginatedResponse<Category>>("/categories", {
      params: { page_size: 200 },
    });
    return data.items;
  },
};

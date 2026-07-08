import { http } from "@/lib/http";
import type { Unit, UnitFormValues } from "@/types/unit";
import type { PaginatedResponse } from "@/types/common";

function toPayload(values: UnitFormValues) {
  return {
    name: values.name,
    short_name: values.short_name,
    conversion_factor: values.conversion_factor ?? null,
    is_active: values.is_active,
  };
}

export const unitService = {
  async list(): Promise<Unit[]> {
    const { data } = await http.get<PaginatedResponse<Unit>>("/units", {
      params: { page_size: 200 },
    });
    return data.items;
  },

  async create(values: UnitFormValues): Promise<Unit> {
    const { data } = await http.post<Unit>("/units", toPayload(values));
    return data;
  },

  async update(id: number, values: UnitFormValues): Promise<Unit> {
    const { data } = await http.put<Unit>(`/units/${id}`, toPayload(values));
    return data;
  },

  async remove(id: number): Promise<void> {
    await http.delete(`/units/${id}`);
  },
};

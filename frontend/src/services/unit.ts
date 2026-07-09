import { http } from "@/lib/http";
import type { Unit } from "@/types/unit";
import type { PaginatedResponse } from "@/types/common";

export interface UnitCreateInput {
  name: string;
  short_name: string;
}

export const unitService = {
  async list(): Promise<Unit[]> {
    const { data } = await http.get<PaginatedResponse<Unit>>("/units", {
      params: { page_size: 200 },
    });
    return data.items;
  },

  async create(values: UnitCreateInput): Promise<Unit> {
    const { data } = await http.post<Unit>("/units", values);
    return data;
  },
};

import { http } from "@/lib/http";
import type { Store, StoreFormValues } from "@/types/store";

export const storeService = {
  async list(): Promise<Store[]> {
    const { data } = await http.get<Store[]>("/stores");
    return data;
  },

  async create(payload: StoreFormValues): Promise<Store> {
    const { data } = await http.post<Store>("/stores", payload);
    return data;
  },

  async update(id: number, payload: StoreFormValues): Promise<Store> {
    const { data } = await http.put<Store>(`/stores/${id}`, payload);
    return data;
  },

  async deactivate(id: number): Promise<Store> {
    const { data } = await http.post<Store>(`/stores/${id}/deactivate`);
    return data;
  },
};

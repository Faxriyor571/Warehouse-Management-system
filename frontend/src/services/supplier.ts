import { http } from "@/lib/http";
import type { Supplier, SupplierFormValues } from "@/types/supplier";
import type { PaginatedResponse } from "@/types/common";

function toPayload(values: SupplierFormValues) {
  return {
    name: values.name,
    phone: values.phone || null,
    address: values.address || null,
    responsible_person: values.responsible_person || null,
    description: values.description || null,
    is_active: values.is_active,
  };
}

export const supplierService = {
  async list(): Promise<Supplier[]> {
    const { data } = await http.get<PaginatedResponse<Supplier>>("/suppliers", {
      params: { page_size: 200 },
    });
    return data.items;
  },

  async create(values: SupplierFormValues): Promise<Supplier> {
    const { data } = await http.post<Supplier>("/suppliers", toPayload(values));
    return data;
  },

  async update(id: number, values: SupplierFormValues): Promise<Supplier> {
    const { data } = await http.put<Supplier>(`/suppliers/${id}`, toPayload(values));
    return data;
  },

  async remove(id: number): Promise<void> {
    await http.delete(`/suppliers/${id}`);
  },
};

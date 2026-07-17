import { http } from "@/lib/http";
import type { Customer, CustomerFormValues } from "@/types/customer";
import type { PaginatedResponse } from "@/types/common";

function toPayload(values: CustomerFormValues) {
  return {
    full_name: values.full_name || null,
    customer_type: values.customer_type,
    phone: values.phone || null,
    address: values.address || null,
    passport: values.passport || null,
    description: values.description || null,
    is_active: values.is_active,
  };
}

export const customerService = {
  async list(): Promise<Customer[]> {
    const { data } = await http.get<PaginatedResponse<Customer>>("/customers", {
      params: { page_size: 200 },
    });
    return data.items;
  },

  async create(values: CustomerFormValues): Promise<Customer> {
    const { data } = await http.post<Customer>("/customers", toPayload(values));
    return data;
  },

  async update(id: number, values: CustomerFormValues): Promise<Customer> {
    const { data } = await http.put<Customer>(`/customers/${id}`, toPayload(values));
    return data;
  },

  async deactivate(id: number): Promise<Customer> {
    const { data } = await http.post<Customer>(`/customers/${id}/deactivate`);
    return data;
  },
};

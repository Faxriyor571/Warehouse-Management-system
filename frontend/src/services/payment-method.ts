import { http } from "@/lib/http";
import type { PaymentMethod, PaymentMethodFormValues } from "@/types/payment-method";

export const paymentMethodService = {
  async list(): Promise<PaymentMethod[]> {
    const { data } = await http.get<PaymentMethod[]>("/payment-methods");
    return data;
  },

  async create(values: PaymentMethodFormValues): Promise<PaymentMethod> {
    const { data } = await http.post<PaymentMethod>("/payment-methods", values);
    return data;
  },

  async update(id: number, values: PaymentMethodFormValues): Promise<PaymentMethod> {
    const { data } = await http.put<PaymentMethod>(`/payment-methods/${id}`, values);
    return data;
  },

  async remove(id: number): Promise<void> {
    await http.delete(`/payment-methods/${id}`);
  },
};

import { http } from "@/lib/http";
import type { PaginatedResponse } from "@/types/common";
import type {
  Debt,
  DebtDetail,
  DebtDueDateFormValues,
  DebtListParams,
  DebtPayment,
  DebtPaymentFormValues,
} from "@/types/debt";

export const debtService = {
  async list(params: DebtListParams): Promise<PaginatedResponse<Debt>> {
    const { data } = await http.get<PaginatedResponse<Debt>>("/debts", {
      params: { ...params, page_size: 20 },
    });
    return data;
  },

  async get(id: number): Promise<DebtDetail> {
    const { data } = await http.get<DebtDetail>(`/debts/${id}`);
    return data;
  },

  async addPayment(id: number, values: DebtPaymentFormValues): Promise<DebtPayment> {
    const { data } = await http.post<DebtPayment>(`/debts/${id}/payments`, {
      amount: values.amount,
      payment_method_id: Number(values.payment_method_id),
      note: values.note || null,
    });
    return data;
  },

  async updateDueDate(id: number, values: DebtDueDateFormValues): Promise<Debt> {
    const { data } = await http.put<Debt>(`/debts/${id}/due-date`, {
      due_date: values.due_date || null,
    });
    return data;
  },
};

import { http } from "@/lib/http";
import type { PaginatedResponse } from "@/types/common";
import type { Expense, ExpenseFormValues, ExpenseListParams } from "@/types/expense";

export const expenseService = {
  async list(params: ExpenseListParams): Promise<PaginatedResponse<Expense>> {
    const { data } = await http.get<PaginatedResponse<Expense>>("/expenses", {
      params: { ...params, page_size: 20 },
    });
    return data;
  },

  async create(values: ExpenseFormValues): Promise<Expense> {
    const { data } = await http.post<Expense>("/expenses", {
      store_id: values.store_id ? Number(values.store_id) : undefined,
      expense_type: values.expense_type,
      amount: values.amount,
      description: values.description,
      date: values.date || undefined,
    });
    return data;
  },
};

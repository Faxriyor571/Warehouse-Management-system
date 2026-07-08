import type { UserBrief } from "./common";

export type ExpenseType = "fuel" | "driver" | "loader" | "other";

export interface Expense {
  id: number;
  company_id: number | null;
  store_id: number | null;
  created_by_id: number;
  expense_type: ExpenseType;
  amount: string;
  description: string;
  date: string;
  created_at: string;
  created_by: UserBrief | null;
}

export interface ExpenseListParams {
  store_id?: number;
  expense_type?: ExpenseType;
  date_from?: string;
  date_to?: string;
}

export interface ExpenseFormValues {
  store_id?: string;
  expense_type: ExpenseType;
  amount: number;
  description: string;
  date?: string;
}

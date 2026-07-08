export type DebtStatus = "active" | "paid" | "overdue";

export interface DebtPayment {
  id: number;
  debt_id: number;
  amount: string;
  payment_method_id: number;
  date: string;
  note: string | null;
  payment_method: { id: number; name: string; type: string } | null;
}

export interface Debt {
  id: number;
  company_id: number | null;
  store_id: number | null;
  customer_id: number;
  stock_out_id: number | null;
  amount: string;
  paid_amount: string;
  remaining_amount: string;
  start_date: string;
  due_date: string | null;
  status: DebtStatus;
  note: string | null;
  created_at: string;
  customer: { id: number; full_name: string } | null;
}

export interface DebtDetail extends Debt {
  payments: DebtPayment[];
}

export interface DebtListParams {
  store_id?: number;
  customer_id?: number;
  status?: DebtStatus;
  only_open?: boolean;
  due_before?: string;
  due_after?: string;
}

export interface DebtPaymentFormValues {
  amount: number;
  payment_method_id: string;
  note?: string;
}

export interface DebtDueDateFormValues {
  due_date?: string;
}

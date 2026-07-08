export type PaymentStatus = "paid" | "partial" | "unpaid";

export interface SaleItem {
  id: number;
  product_id: number;
  quantity: string;
  price: string;
  discount: string;
  subtotal: string;
  product: { id: number; name: string; sku: string } | null;
}

export interface SalePayment {
  id: number;
  stock_out_id: number;
  payment_method_id: number;
  amount: string;
  date: string;
  note: string | null;
  payment_method: { id: number; name: string; type: string } | null;
}

export interface Sale {
  id: number;
  reference: string;
  store_id: number | null;
  customer_id: number | null;
  created_by_id: number;
  date: string;
  subtotal: string;
  discount: string;
  total_amount: string;
  paid_amount: string;
  payment_status: PaymentStatus;
  note: string | null;
  created_at: string;
  customer: { id: number; full_name: string } | null;
  created_by: { id: number; full_name: string } | null;
  items: SaleItem[];
  payments: SalePayment[];
}

export interface SaleListParams {
  store_id?: number;
  customer_id?: number;
  payment_status?: PaymentStatus;
  search?: string;
  date_from?: string;
  date_to?: string;
}

export interface SaleItemFormValues {
  product_id: string;
  quantity: number;
  price?: number;
  discount: number;
}

export interface SalePaymentFormValues {
  payment_method_id: string;
  amount: number;
  note?: string;
}

export interface SaleFormValues {
  store_id?: string;
  customer_id?: string;
  date?: string;
  discount: number;
  note?: string;
  due_date?: string;
  items: SaleItemFormValues[];
  payments: SalePaymentFormValues[];
}

export interface SalesReturnItem {
  id: number;
  stock_out_item_id: number;
  product_id: number;
  quantity: string;
  price: string;
  subtotal: string;
}

export interface SalesReturn {
  id: number;
  reference: string;
  store_id: number | null;
  stock_out_id: number;
  created_by_id: number;
  date: string;
  reason: string | null;
  total_amount: string;
  created_at: string;
  items: SalesReturnItem[];
}

export interface SalesReturnFormValues {
  reason?: string;
  items: { stock_out_item_id: number; quantity: number }[];
}

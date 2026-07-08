import type { ProductBrief, UserBrief } from "./common";

export interface StockInItem {
  id: number;
  product_id: number;
  quantity: string;
  price: string;
  subtotal: string;
  product: ProductBrief | null;
}

export interface StockIn {
  id: number;
  reference: string;
  store_id: number | null;
  created_by_id: number;
  date: string;
  total_amount: string;
  note: string | null;
  created_by: UserBrief | null;
  items: StockInItem[];
}

export interface StockInListParams {
  store_id?: number;
  search?: string;
  date_from?: string;
  date_to?: string;
}

export interface StockInItemFormValues {
  product_id: string;
  quantity: number;
  price: number;
}

export interface StockInFormValues {
  store_id?: string;
  date?: string;
  note?: string;
  items: StockInItemFormValues[];
}

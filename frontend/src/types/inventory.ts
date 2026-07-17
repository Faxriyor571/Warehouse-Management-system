export type MovementType = "stock_in" | "sale" | "sales_return" | "adjustment";

export interface StoreStockRow {
  product_id: number;
  product_name: string;
  sku: string;
  quantity: string;
}

export interface CrossStoreRow {
  store_id: number;
  store_name: string;
  quantity: string;
}

export interface StockMovement {
  id: number;
  store_id: number;
  product_id: number;
  movement_type: MovementType;
  quantity_delta: string;
  reference_type: string;
  reference_id: number | null;
  created_by: string | null;
  created_at: string;
}

export interface StoreStockListParams {
  store_id?: number;
  search?: string;
}

export interface MovementListParams {
  store_id?: number;
  product_id?: number;
  movement_type?: MovementType;
  date_from?: string;
  date_to?: string;
}

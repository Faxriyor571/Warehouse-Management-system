export interface TopProduct {
  product_id: number;
  name: string;
  quantity_sold: string;
  revenue: string;
}

export interface TopDebtor {
  customer_id: number;
  full_name: string;
  remaining: string;
}

export interface RecentOperation {
  type: "sale" | "stock_in";
  reference: string;
  date: string;
  amount: string;
}

export interface ChartPoint {
  label: string;
  value: string;
}

export interface DashboardStats {
  scope: "store" | "company";
  today_sales_total: string;
  today_sales_count: number;
  month_revenue: string;
  month_expenses: string;
  debtors_count: number;
  debtors_total: string;
  top_products: TopProduct[];
  top_debtors: TopDebtor[];
  recent_operations: RecentOperation[];
  sales_chart: ChartPoint[];
}

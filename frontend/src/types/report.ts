export interface ChartPoint {
  label: string;
  value: string;
}

export interface PaymentStatusBucket {
  status: string;
  count: number;
  revenue: string;
}

export interface SalesReport {
  total_revenue: string;
  total_count: number;
  by_payment_status: PaymentStatusBucket[];
  by_day: ChartPoint[];
}

export interface InventoryReportRow {
  product_id: number;
  name: string;
  sku: string;
  quantity: string;
}

export interface InventoryReport {
  rows: InventoryReportRow[];
  count: number;
}

export interface DebtByCustomer {
  customer_id: number;
  full_name: string;
  remaining: string;
}

export interface DebtByStatus {
  status: string;
  count: number;
  remaining: string;
}

export interface DebtReport {
  by_customer: DebtByCustomer[];
  by_status: DebtByStatus[];
  total_remaining: string;
}

export interface ExpenseByType {
  expense_type: string;
  total: string;
  count: number;
}

export interface ExpenseReport {
  by_type: ExpenseByType[];
  by_date: ChartPoint[];
  total: string;
}

export interface ReportParams {
  store_id?: number;
  date_from?: string;
  date_to?: string;
}

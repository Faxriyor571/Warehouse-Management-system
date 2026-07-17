import { http } from "@/lib/http";
import type {
  DebtReport,
  ExpenseReport,
  InventoryReport,
  ReportParams,
  SalesReport,
} from "@/types/report";

export const reportService = {
  async sales(params: ReportParams): Promise<SalesReport> {
    const { data } = await http.get<SalesReport>("/reports/sales", { params });
    return data;
  },

  async inventory(params: Pick<ReportParams, "store_id">): Promise<InventoryReport> {
    const { data } = await http.get<InventoryReport>("/reports/inventory", { params });
    return data;
  },

  async debts(params: Pick<ReportParams, "store_id">): Promise<DebtReport> {
    const { data } = await http.get<DebtReport>("/reports/debts", { params });
    return data;
  },

  async expenses(params: Pick<ReportParams, "store_id">): Promise<ExpenseReport> {
    const { data } = await http.get<ExpenseReport>("/reports/expenses", { params });
    return data;
  },
};

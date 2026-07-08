import { http } from "@/lib/http";
import type { DashboardStats } from "@/types/dashboard";

export const dashboardService = {
  async getStats(): Promise<DashboardStats> {
    const { data } = await http.get<DashboardStats>("/dashboard");
    return data;
  },
};

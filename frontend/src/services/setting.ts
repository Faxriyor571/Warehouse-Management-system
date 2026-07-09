import { http } from "@/lib/http";
import type { Company } from "@/types/company";

export const settingService = {
  async getCompany(): Promise<Company> {
    const { data } = await http.get<Company>("/settings/company");
    return data;
  },

  async updateCompany(name: string): Promise<Company> {
    const { data } = await http.put<Company>("/settings/company", { name });
    return data;
  },
};

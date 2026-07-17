import { http } from "@/lib/http";
import type { PaginatedResponse } from "@/types/common";
import type {
  Company,
  CompanyCreateInput,
  CompanyCreateResponse,
  CompanyStatus,
  CompanyUpdateInput,
  SupportSessionResponse,
} from "@/types/company";

export interface CompanyListParams {
  search?: string;
  status?: CompanyStatus;
  page?: number;
  page_size?: number;
}

export const companyService = {
  async list(params: CompanyListParams = {}): Promise<PaginatedResponse<Company>> {
    const { data } = await http.get<PaginatedResponse<Company>>("/companies", {
      params: { page_size: 200, ...params },
    });
    return data;
  },

  async create(payload: CompanyCreateInput): Promise<CompanyCreateResponse> {
    const { data } = await http.post<CompanyCreateResponse>("/companies", payload);
    return data;
  },

  async update(id: number, payload: CompanyUpdateInput): Promise<Company> {
    const { data } = await http.put<Company>(`/companies/${id}`, payload);
    return data;
  },

  async activate(id: number): Promise<Company> {
    const { data } = await http.post<Company>(`/companies/${id}/activate`);
    return data;
  },

  async suspend(id: number): Promise<Company> {
    const { data } = await http.post<Company>(`/companies/${id}/suspend`);
    return data;
  },

  async startSupportSession(id: number): Promise<SupportSessionResponse> {
    const { data } = await http.post<SupportSessionResponse>(`/companies/${id}/support-session`);
    return data;
  },
};

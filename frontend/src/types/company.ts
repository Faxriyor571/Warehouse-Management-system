export type CompanyStatus = "active" | "suspended";

export interface Company {
  id: number;
  name: string;
  slug: string;
  status: CompanyStatus;
  contact_email: string | null;
  contact_phone: string | null;
  created_at: string;
  updated_at: string;
}

export interface CeoSummary {
  id: number;
  username: string;
  full_name: string;
  email: string | null;
}

export interface CompanyUpdateInput {
  name: string;
  contact_email?: string | null;
  contact_phone?: string | null;
}

export interface CompanyCreateInput {
  name: string;
  slug: string;
  contact_email?: string | null;
  contact_phone?: string | null;
  ceo: {
    username: string;
    full_name: string;
    password: string;
    email?: string | null;
  };
}

export interface CompanyCreateResponse {
  company: Company;
  ceo: CeoSummary;
}

export interface SupportSessionResponse {
  access_token: string;
  token_type: string;
  company: Company;
}

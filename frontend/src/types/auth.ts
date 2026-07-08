export type UserRole = "super_admin" | "ceo" | "seller";

export interface User {
  id: number;
  username: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  is_superuser: boolean;
  role_id: number | null;
  role: UserRole | null;
  company_id: number | null;
  store_id: number | null;
  last_login_at: string | null;
  created_at: string;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

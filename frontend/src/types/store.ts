export interface Store {
  id: number;
  company_id?: number;
  name: string;
  address: string | null;
  phone: string | null;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface StoreFormValues {
  name: string;
  address?: string;
}

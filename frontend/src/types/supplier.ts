export interface Supplier {
  id: number;
  name: string;
  phone: string | null;
  address: string | null;
  responsible_person: string | null;
  description: string | null;
  is_active: boolean;
}

export interface SupplierFormValues {
  name: string;
  phone?: string;
  address?: string;
  responsible_person?: string;
  description?: string;
  is_active: boolean;
}

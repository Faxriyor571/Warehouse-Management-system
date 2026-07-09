export type CustomerType = "individual" | "legal_entity";

export interface Customer {
  id: number;
  full_name: string;
  customer_type: CustomerType | null;
  phone: string | null;
  address: string | null;
  passport: string | null;
  description: string | null;
  is_active: boolean;
}

export interface CustomerFormValues {
  /** Optional for an Individual customer — required for a Legal Entity (enforced by the form's Zod schema). */
  full_name?: string;
  customer_type: CustomerType;
  phone?: string;
  address?: string;
  passport?: string;
  description?: string;
  is_active: boolean;
}

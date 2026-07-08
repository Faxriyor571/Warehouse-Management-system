export interface PaymentMethod {
  id: number;
  company_id: number | null;
  name: string;
  type: string;
  is_system: boolean;
  is_active: boolean;
}

export interface PaymentMethodFormValues {
  name: string;
  type: string;
  is_active: boolean;
}

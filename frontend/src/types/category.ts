export interface Category {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CategoryFormValues {
  name: string;
  description?: string;
  is_active: boolean;
}

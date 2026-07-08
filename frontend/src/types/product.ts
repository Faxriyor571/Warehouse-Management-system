import type { Category } from "./category";
import type { Unit } from "./unit";

export interface Product {
  id: number;
  name: string;
  sku: string;
  barcode: string | null;
  category_id: number;
  unit_id: number;
  purchase_price: string;
  sale_price: string;
  description: string | null;
  is_active: boolean;
  category: Category | null;
  unit: Unit | null;
}

export interface ProductFormValues {
  name: string;
  sku: string;
  barcode?: string;
  category_id: string;
  unit_id: string;
  purchase_price: number;
  sale_price: number;
  description?: string;
  is_active: boolean;
}

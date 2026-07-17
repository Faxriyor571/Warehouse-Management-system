export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  meta: PageMeta;
}

/** Minimal user reference embedded in other resources (e.g. `created_by`). */
export interface UserBrief {
  id: number;
  full_name: string;
}

/** Minimal customer reference embedded in other resources (e.g. a sale's `customer`). */
export interface CustomerBrief {
  id: number;
  full_name: string;
}

/** Minimal payment method reference embedded in payment records. */
export interface PaymentMethodBrief {
  id: number;
  name: string;
  type: string;
}

/** Minimal product reference embedded in stock-in/sale line items. */
export interface ProductBrief {
  id: number;
  name: string;
  sku: string;
}

import { http } from "@/lib/http";
import type { PaginatedResponse } from "@/types/common";
import type {
  CrossStoreRow,
  MovementListParams,
  StockMovement,
  StoreStockListParams,
  StoreStockRow,
} from "@/types/inventory";

export const inventoryService = {
  async storeStock(params: StoreStockListParams): Promise<PaginatedResponse<StoreStockRow>> {
    const { data } = await http.get<PaginatedResponse<StoreStockRow>>("/inventory/store-stock", {
      params: { ...params, page_size: 50 },
    });
    return data;
  },

  async crossStore(productId: number): Promise<CrossStoreRow[]> {
    const { data } = await http.get<CrossStoreRow[]>("/inventory/store-stock/cross-store", {
      params: { product_id: productId },
    });
    return data;
  },

  async movements(params: MovementListParams): Promise<PaginatedResponse<StockMovement>> {
    const { data } = await http.get<PaginatedResponse<StockMovement>>("/inventory/movements", {
      params: { ...params, page_size: 50 },
    });
    return data;
  },
};

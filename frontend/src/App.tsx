import axios from "axios";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";
import { AuthProvider } from "@/providers/auth-provider";
import CategoriesPage from "@/pages/CategoriesPage";
import CustomersPage from "@/pages/CustomersPage";
import DashboardPage from "@/pages/DashboardPage";
import DebtDetailPage from "@/pages/DebtDetailPage";
import DebtsPage from "@/pages/DebtsPage";
import ExpensesPage from "@/pages/ExpensesPage";
import LoginPage from "@/pages/LoginPage";
import PaymentMethodsPage from "@/pages/PaymentMethodsPage";
import ProductsPage from "@/pages/ProductsPage";
import ReportsPage from "@/pages/ReportsPage";
import SalesDetailPage from "@/pages/SalesDetailPage";
import SalesNewPage from "@/pages/SalesNewPage";
import SalesPage from "@/pages/SalesPage";
import SettingsPage from "@/pages/SettingsPage";
import StockInDetailPage from "@/pages/StockInDetailPage";
import StockInNewPage from "@/pages/StockInNewPage";
import StockInPage from "@/pages/StockInPage";
import StoresPage from "@/pages/StoresPage";
import SuppliersPage from "@/pages/SuppliersPage";
import UnitsPage from "@/pages/UnitsPage";

/**
 * Never retry 4xx client errors (permission/validation/not-found) — they
 * won't succeed no matter how many times we ask. Retrying only masked the
 * real problem: while a retry is pending, the query sits in a "paused"
 * fetchStatus for several seconds and `isError` never becomes true until
 * retries are exhausted, so error UI (permission-denied, 404, etc.) looked
 * broken. Real network/5xx failures still get a couple of retries.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (axios.isAxiosError(error) && error.response && error.response.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster richColors position="top-right" />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/stores" element={<StoresPage />} />
                <Route path="/products" element={<ProductsPage />} />
                <Route path="/categories" element={<CategoriesPage />} />
                <Route path="/units" element={<UnitsPage />} />
                <Route path="/suppliers" element={<SuppliersPage />} />
                <Route path="/customers" element={<CustomersPage />} />
                <Route path="/stock-in" element={<StockInPage />} />
                <Route path="/stock-in/new" element={<StockInNewPage />} />
                <Route path="/stock-in/:id" element={<StockInDetailPage />} />
                <Route path="/sales" element={<SalesPage />} />
                <Route path="/sales/new" element={<SalesNewPage />} />
                <Route path="/sales/:id" element={<SalesDetailPage />} />
                <Route path="/debts" element={<DebtsPage />} />
                <Route path="/debts/:id" element={<DebtDetailPage />} />
                <Route path="/expenses" element={<ExpensesPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/payment-methods" element={<PaymentMethodsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

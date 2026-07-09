import { lazy, Suspense } from "react";
import axios from "axios";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/app-shell";
import { PageLoader } from "@/components/feedback/page-loader";
import { AuthProvider } from "@/providers/auth-provider";
import LoginPage from "@/pages/LoginPage";

const CategoriesPage = lazy(() => import("@/pages/CategoriesPage"));
const CompaniesPage = lazy(() => import("@/pages/CompaniesPage"));
const CustomersPage = lazy(() => import("@/pages/CustomersPage"));
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const DebtDetailPage = lazy(() => import("@/pages/DebtDetailPage"));
const DebtsPage = lazy(() => import("@/pages/DebtsPage"));
const EmployeesPage = lazy(() => import("@/pages/EmployeesPage"));
const ExpensesPage = lazy(() => import("@/pages/ExpensesPage"));
const InventoryPage = lazy(() => import("@/pages/InventoryPage"));
const PaymentMethodsPage = lazy(() => import("@/pages/PaymentMethodsPage"));
const ProductsPage = lazy(() => import("@/pages/ProductsPage"));
const ReportsPage = lazy(() => import("@/pages/ReportsPage"));
const SalesDetailPage = lazy(() => import("@/pages/SalesDetailPage"));
const SalesNewPage = lazy(() => import("@/pages/SalesNewPage"));
const SalesPage = lazy(() => import("@/pages/SalesPage"));
const SettingsPage = lazy(() => import("@/pages/SettingsPage"));
const StockInDetailPage = lazy(() => import("@/pages/StockInDetailPage"));
const StockInNewPage = lazy(() => import("@/pages/StockInNewPage"));
const StockInPage = lazy(() => import("@/pages/StockInPage"));
const StoresPage = lazy(() => import("@/pages/StoresPage"));

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
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AuthProvider>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<ProtectedRoute />}>
                <Route element={<AppShell />}>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/companies" element={<CompaniesPage />} />
                  <Route path="/stores" element={<StoresPage />} />
                  <Route path="/employees" element={<EmployeesPage />} />
                  <Route path="/products" element={<ProductsPage />} />
                  <Route path="/categories" element={<CategoriesPage />} />
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
                  <Route path="/inventory" element={<InventoryPage />} />
                  <Route path="/reports" element={<ReportsPage />} />
                  <Route path="/payment-methods" element={<PaymentMethodsPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Route>
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

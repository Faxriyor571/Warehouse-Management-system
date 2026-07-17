/**
 * Frontend mirror of the backend permission matrix
 * (`app/permissions/employee_matrix.py`). Kept in sync manually — same
 * pattern already used for other enums shared across the two codebases
 * (e.g. `MovementType`). Adding a future job function (Manager, Auditor...)
 * means adding one value to `EmployeeRole` (types/auth.ts) plus one entry in
 * `EMPLOYEE_ROLE_PERMS` below, on both sides — nothing else changes.
 */
import type { EmployeeRole, User, UserRole } from "@/types/auth";

export type Perm =
  | "dashboard.view"
  | "reports.sales"
  | "reports.inventory"
  | "reports.debts"
  | "reports.expenses"
  | "reports.financial"
  | "stores.manage"
  | "employees.manage"
  | "products.view"
  | "products.manage"
  | "categories.view"
  | "categories.manage"
  | "sales.view"
  | "sales.manage"
  | "debts.manage"
  | "stock_in.view"
  | "stock_in.manage"
  | "inventory.view"
  | "transfer.view"
  | "transfer.manage"
  | "expenses.manage"
  | "payroll.manage"
  | "withdrawals.manage"
  | "settings.manage"
  | "customers.view"
  | "customers.manage"
  | "suppliers.manage"
  | "payment_methods.view"
  | "payment_methods.manage";

const ALL_PERMS: Perm[] = [
  "dashboard.view",
  "reports.sales",
  "reports.inventory",
  "reports.debts",
  "reports.expenses",
  "reports.financial",
  "stores.manage",
  "employees.manage",
  "products.view",
  "products.manage",
  "categories.view",
  "categories.manage",
  "sales.view",
  "sales.manage",
  "debts.manage",
  "stock_in.view",
  "stock_in.manage",
  "inventory.view",
  "transfer.view",
  "transfer.manage",
  "expenses.manage",
  "payroll.manage",
  "withdrawals.manage",
  "settings.manage",
  "customers.view",
  "customers.manage",
  "suppliers.manage",
  "payment_methods.view",
  "payment_methods.manage",
];

// The Company Owner (CEO) manages the business but does not perform daily
// operational data entry: full view/manage everywhere except executing a
// sale, receiving inventory, or moving stock between stores — those are
// employee responsibilities.
const CEO_EXCLUDED: Perm[] = ["sales.manage", "stock_in.manage", "transfer.manage"];
const CEO_PERMS = new Set<Perm>(ALL_PERMS.filter((p) => !CEO_EXCLUDED.includes(p)));

const EMPLOYEE_ROLE_PERMS: Record<EmployeeRole, Set<Perm>> = {
  cashier: new Set<Perm>([
    "dashboard.view",
    "products.view",
    "categories.view",
    "sales.view",
    "sales.manage",
    "debts.manage",
    "customers.view",
    "payment_methods.view",
  ]),
  warehouse: new Set<Perm>([
    "dashboard.view",
    "products.view",
    "categories.view",
    "stock_in.view",
    "stock_in.manage",
    "inventory.view",
    "transfer.view",
    "transfer.manage",
    "suppliers.manage",
  ]),
  accountant: new Set<Perm>([
    "dashboard.view",
    "expenses.manage",
    "payroll.manage",
    "withdrawals.manage",
    "debts.manage",
    "reports.debts",
    "reports.expenses",
    "reports.financial",
  ]),
};

function permissionsFor(role: UserRole | null, employeeRole: EmployeeRole | null): Set<Perm> {
  if (role === "ceo") return CEO_PERMS;
  if (role === "seller") return employeeRole ? EMPLOYEE_ROLE_PERMS[employeeRole] : new Set();
  return new Set();
}

/** True if `user` has `perm` — the legacy single-tenant admin (`role === null`,
 * `is_superuser`) bypasses everything, matching the backend's `require_perm`. */
export function hasPerm(user: User | null, perm: Perm): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  return permissionsFor(user.role, user.employee_role).has(perm);
}

/** True if `user` has at least one of `perms` (e.g. gating a single Reports
 * nav link that fans out into several independently-permissioned tabs). */
export function hasAnyPerm(user: User | null, perms: Perm[]): boolean {
  return perms.some((p) => hasPerm(user, p));
}

/**
 * True unless `user` is store-confined (a Cashier — the one job function
 * whose store comes from their token, never a choice). CEO, Warehouse
 * Employee, and Accountant are all company-wide, exactly mirroring the
 * backend's `resolve_scope` (app/utils/scope.py) split — use this to decide
 * whether a page should show a store picker/filter at all.
 */
export function isCompanyWide(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  if (user.role === "ceo") return true;
  return user.role === "seller" && user.employee_role !== "cashier";
}

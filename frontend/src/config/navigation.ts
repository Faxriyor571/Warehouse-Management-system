import {
  BarChart3,
  Boxes,
  Building2,
  CreditCard,
  Download,
  LayoutDashboard,
  Receipt,
  Settings,
  ShoppingCart,
  Store,
  Tag,
  UserCog,
  Wallet,
  Warehouse,
  type LucideIcon,
} from "lucide-react";

import type { Perm } from "@/lib/permissions";

export interface NavItem {
  id: string;
  title: string;
  href: string;
  icon: LucideIcon;
  /**
   * Gates visibility via `hasPerm` (see lib/permissions.ts) — the SAME
   * permission code the backend checks, so the sidebar can never show a
   * module the API would reject. Omit for items visible to every signed-in
   * identity (currently only Dashboard). System Owner (`role === "super_admin"`)
   * holds no business Perm at all — `superAdminOnly` is the one exception,
   * for the platform-level Companies module.
   */
  perm?: Perm;
  /** Visible only to `role === "super_admin"` (platform-level, above every company). */
  superAdminOnly?: boolean;
  /** Visible if the user holds ANY of these perms (Reports has one link but several independently-gated tabs). */
  anyOfPerms?: Perm[];
  /**
   * `perm`'s `hasPerm` check bypasses to true for the legacy admin
   * (`is_superuser`), mirroring `require_perm`'s bypass on every migrated
   * router. Employees is one of the few routers NOT migrated — it still
   * uses the old, strict `RequireCEO` with no legacy-admin branch — so its
   * item must check `role === "ceo"` literally instead of trusting `perm`.
   */
  strictCeoOnly?: boolean;
}

/**
 * One flat list of modules — no section headers. Adding a future role
 * (Manager, Auditor, ...) never touches this file: it's driven entirely by
 * `Perm` grants resolved in `lib/permissions.ts`.
 */
export const navItems: NavItem[] = [
  { id: "dashboard", title: "Boshqaruv paneli", href: "/", icon: LayoutDashboard },
  { id: "companies", title: "Kompaniyalar", href: "/companies", icon: Building2, superAdminOnly: true },
  { id: "stores", title: "Do'konlar", href: "/stores", icon: Store, perm: "stores.manage" },
  { id: "employees", title: "Xodimlar", href: "/employees", icon: UserCog, strictCeoOnly: true },
  { id: "products", title: "Mahsulotlar", href: "/products", icon: Boxes, perm: "products.view" },
  { id: "categories", title: "Kategoriyalar", href: "/categories", icon: Tag, perm: "categories.manage" },
  { id: "stock-in", title: "Kirim", href: "/stock-in", icon: Download, perm: "stock_in.view" },
  { id: "sales", title: "Savdo", href: "/sales", icon: ShoppingCart, perm: "sales.view" },
  { id: "inventory", title: "Ombor", href: "/inventory", icon: Warehouse, perm: "inventory.view" },
  { id: "debts", title: "Qarzlar", href: "/debts", icon: Wallet, perm: "debts.manage" },
  { id: "expenses", title: "Xarajatlar", href: "/expenses", icon: Receipt, perm: "expenses.manage" },
  {
    id: "reports",
    title: "Hisobotlar",
    href: "/reports",
    icon: BarChart3,
    anyOfPerms: ["reports.sales", "reports.inventory", "reports.debts", "reports.expenses", "reports.financial"],
  },
  { id: "payment-methods", title: "To'lov turlari", href: "/payment-methods", icon: CreditCard, perm: "payment_methods.manage" },
  { id: "settings", title: "Sozlamalar", href: "/settings", icon: Settings, perm: "settings.manage" },
];

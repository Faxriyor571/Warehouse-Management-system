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

import type { UserRole } from "@/types/auth";

export interface NavItem {
  id: string;
  title: string;
  href: string;
  icon: LucideIcon;
  /**
   * Omit to show to every *tenant* identity (CEO, Seller, and the legacy
   * admin, role === null) — never to the System Owner (role === "super_admin"),
   * who operates above all companies and has no access to any tenant's
   * business data outside a support session (SRS §3.1). System-Owner-only
   * items must opt in explicitly with `roles: ["super_admin"]`.
   */
  roles?: Array<UserRole | null>;
}

export interface NavSection {
  id: string;
  label?: string;
  items: NavItem[];
}

export const navSections: NavSection[] = [
  {
    id: "main",
    items: [{ id: "dashboard", title: "Boshqaruv paneli", href: "/", icon: LayoutDashboard }],
  },
  {
    id: "platform",
    label: "PLATFORMA",
    // System Owner only — platform-level tenant management, above every company.
    items: [{ id: "companies", title: "Kompaniyalar", href: "/companies", icon: Building2, roles: ["super_admin"] }],
  },
  {
    id: "company",
    label: "KOMPANIYA",
    items: [
      { id: "stores", title: "Do'konlar", href: "/stores", icon: Store },
      // CEO only (strict — RequireCEO has no legacy-admin branch, unlike
      // most other modules). A Seller has no backend access either.
      { id: "employees", title: "Sotuvchilar", href: "/employees", icon: UserCog, roles: ["ceo"] },
    ],
  },
  {
    id: "catalogue",
    label: "KATALOG",
    items: [
      { id: "products", title: "Mahsulotlar", href: "/products", icon: Boxes },
      { id: "categories", title: "Kategoriyalar", href: "/categories", icon: Tag },
    ],
  },
  {
    id: "operations",
    label: "OPERATSIYALAR",
    items: [
      { id: "stock-in", title: "Kirim", href: "/stock-in", icon: Download },
      { id: "sales", title: "Savdo", href: "/sales", icon: ShoppingCart },
      { id: "debts", title: "Qarzlar", href: "/debts", icon: Wallet },
      { id: "expenses", title: "Xarajatlar", href: "/expenses", icon: Receipt },
      // CEO or Seller only (strict — RequireCEOOrSeller has no legacy-admin
      // branch, unlike Stock In/Sales/Debts/Expenses).
      { id: "inventory", title: "Ombor", href: "/inventory", icon: Warehouse, roles: ["ceo", "seller"] },
    ],
  },
  {
    id: "insights",
    label: "TAHLIL",
    items: [{ id: "reports", title: "Hisobotlar", href: "/reports", icon: BarChart3 }],
  },
  {
    id: "settings",
    label: "SOZLAMALAR",
    // CEO only (or the legacy admin, role === null) — a Seller has no
    // backend access to Settings or Payment Method management.
    items: [
      { id: "payment-methods", title: "To'lov turlari", href: "/payment-methods", icon: CreditCard, roles: ["ceo", null] },
      { id: "settings", title: "Sozlamalar", href: "/settings", icon: Settings, roles: ["ceo", null] },
    ],
  },
];

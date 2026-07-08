import { Boxes, Download, LayoutDashboard, Ruler, ShoppingCart, Store, Tag, Truck, Users, type LucideIcon } from "lucide-react";

export interface NavItem {
  id: string;
  title: string;
  href: string;
  icon: LucideIcon;
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
    id: "company",
    label: "KOMPANIYA",
    items: [{ id: "stores", title: "Do'konlar", href: "/stores", icon: Store }],
  },
  {
    id: "catalogue",
    label: "KATALOG",
    items: [
      { id: "products", title: "Mahsulotlar", href: "/products", icon: Boxes },
      { id: "categories", title: "Kategoriyalar", href: "/categories", icon: Tag },
      { id: "units", title: "Birliklar", href: "/units", icon: Ruler },
    ],
  },
  {
    id: "partners",
    label: "HAMKORLAR",
    items: [
      { id: "suppliers", title: "Yetkazib beruvchilar", href: "/suppliers", icon: Truck },
      { id: "customers", title: "Mijozlar", href: "/customers", icon: Users },
    ],
  },
  {
    id: "operations",
    label: "OPERATSIYALAR",
    items: [
      { id: "stock-in", title: "Kirim", href: "/stock-in", icon: Download },
      { id: "sales", title: "Savdo", href: "/sales", icon: ShoppingCart },
    ],
  },
];

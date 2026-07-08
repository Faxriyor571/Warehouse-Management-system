import { LayoutDashboard, Store, type LucideIcon } from "lucide-react";

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
];

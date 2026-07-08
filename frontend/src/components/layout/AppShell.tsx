import { NavLink, Outlet } from "react-router-dom";
import { Warehouse } from "lucide-react";

import { cn } from "@/lib/utils";
import { navSections } from "@/config/navigation";
import { Topbar } from "./Topbar";

export function AppShell() {
  return (
    <div className="grid min-h-svh grid-cols-[16rem_1fr]">
      <aside className="flex flex-col gap-6 border-r bg-card px-3 py-5">
        <div className="flex items-center gap-2.5 px-2 text-base font-semibold tracking-tight">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Warehouse className="size-[18px]" />
          </span>
          Ombor Boshqaruv
        </div>

        <nav aria-label="Asosiy" className="flex flex-1 flex-col gap-5 overflow-y-auto">
          {navSections.map((section) => (
            <div key={section.id} className="space-y-0.5">
              {section.label ? (
                <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                  {section.label}
                </p>
              ) : null}
              {section.items.map((item) => (
                <NavLink
                  key={item.id}
                  to={item.href}
                  end={item.href === "/"}
                  className={({ isActive }) =>
                    cn(
                      "group flex items-center gap-2.5 rounded-md border-l-2 px-2.5 py-2 text-sm font-medium transition-all duration-150",
                      isActive
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-transparent text-muted-foreground hover:border-border hover:bg-accent hover:text-foreground"
                    )
                  }
                >
                  <item.icon className="size-4 shrink-0" />
                  <span className="truncate">{item.title}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

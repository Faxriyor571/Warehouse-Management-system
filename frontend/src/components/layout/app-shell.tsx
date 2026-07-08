import * as React from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Warehouse } from "lucide-react";

import { cn } from "@/lib/utils";
import { navSections } from "@/config/navigation";
import { useAuth } from "@/providers/auth-provider";
import { Topbar } from "./topbar";

export function AppShell() {
  const { user } = useAuth();
  const location = useLocation();
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);

  const visibleSections = navSections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => !item.roles || item.roles.includes(user?.role ?? null)),
    }))
    .filter((section) => section.items.length > 0);

  React.useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-svh lg:grid lg:grid-cols-[18rem_1fr]">
      {mobileNavOpen ? (
        <div
          className="fixed inset-0 z-40 bg-slate-950/30 backdrop-blur-[2px] duration-200 animate-in fade-in lg:hidden"
          onClick={() => setMobileNavOpen(false)}
          aria-hidden
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 -translate-x-full flex-col border-r border-border/70 bg-card shadow-elevated transition-transform duration-300 ease-out lg:static lg:z-auto lg:w-auto lg:translate-x-0 lg:shadow-none",
          mobileNavOpen && "translate-x-0"
        )}
      >
        <div className="flex h-16 shrink-0 items-center gap-2.5 border-b border-border/70 px-5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-sm ring-1 ring-primary/20">
            <Warehouse className="size-[18px]" strokeWidth={2.25} />
          </span>
          <span className="truncate text-[15px] font-semibold tracking-tight text-foreground">
            Ombor Boshqaruv
          </span>
        </div>

        <nav
          aria-label="Asosiy"
          className="scrollbar-thin flex flex-1 flex-col gap-6 overflow-y-auto px-3 py-5"
        >
          {visibleSections.map((section) => (
            <div key={section.id} className="space-y-0.5">
              {section.label ? (
                <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/60">
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
                      "group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13.5px] font-medium transition-all duration-150",
                      isActive
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <item.icon
                        className={cn(
                          "size-[17px] shrink-0 transition-colors",
                          isActive ? "text-primary-foreground" : "text-muted-foreground/80 group-hover:text-foreground"
                        )}
                        strokeWidth={2}
                      />
                      <span className="truncate">{item.title}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-col">
        <Topbar onMenuClick={() => setMobileNavOpen((v) => !v)} />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

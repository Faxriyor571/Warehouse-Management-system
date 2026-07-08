import { NavLink, Outlet } from "react-router-dom";
import { LogOut } from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";
import { navSections } from "@/config/navigation";

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="grid min-h-svh grid-cols-[16rem_1fr]">
      <aside className="flex flex-col gap-6 border-r bg-card px-4 py-6">
        <div className="flex items-center gap-2 px-2 text-lg font-semibold">
          <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            O
          </span>
          Ombor Boshqaruv
        </div>

        <nav aria-label="Asosiy" className="flex flex-1 flex-col gap-6">
          {navSections.map((section) => (
            <div key={section.id} className="space-y-1">
              {section.label ? (
                <p className="px-2 text-xs font-medium tracking-wide text-muted-foreground">{section.label}</p>
              ) : null}
              {section.items.map((item) => (
                <NavLink
                  key={item.id}
                  to={item.href}
                  end={item.href === "/"}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2 rounded-md px-2 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    )
                  }
                >
                  <item.icon className="size-4" />
                  {item.title}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="space-y-2 border-t pt-4">
          <p className="truncate px-2 text-sm font-medium">{user?.full_name}</p>
          <button
            onClick={() => void logout()}
            className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <LogOut className="size-4" />
            Chiqish
          </button>
        </div>
      </aside>

      <main className="overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}

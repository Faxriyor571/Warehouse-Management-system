import * as React from "react";
import { useNavigate } from "react-router-dom";
import { Eye, LogOut } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/button";

/** Shown only while a System Owner is inside a support session (viewing a company as its CEO). */
export function SupportSessionBanner() {
  const { user, exitSupportSession } = useAuth();
  const navigate = useNavigate();
  const [isExiting, setIsExiting] = React.useState(false);

  if (!user?.is_support_session) return null;

  const onExit = async () => {
    setIsExiting(true);
    try {
      await exitSupportSession();
      navigate("/companies", { replace: true });
    } catch {
      toast.error("Support sessiondan chiqib bo'lmadi. Qaytadan urinib ko'ring.");
    } finally {
      setIsExiting(false);
    }
  };

  return (
    <div className="flex items-center justify-between gap-3 border-b border-warning/25 bg-warning/10 px-4 py-2 sm:px-6">
      <p className="flex items-center gap-2 text-[13px] font-medium text-warning">
        <Eye className="size-4 shrink-0" strokeWidth={2.25} />
        <span>
          System Owner sifatida <strong className="font-semibold">{user.support_company_name}</strong> nomidan ko'rmoqdasiz
        </span>
      </p>
      <Button variant="outline" size="sm" onClick={() => void onExit()} loading={isExiting} className="border-warning/30 text-warning hover:bg-warning/15">
        <LogOut className="size-3.5" />
        Chiqish
      </Button>
    </div>
  );
}

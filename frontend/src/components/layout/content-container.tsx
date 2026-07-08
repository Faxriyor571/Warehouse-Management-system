import * as React from "react";

import { cn } from "@/lib/utils";

export const ContentContainer = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("mx-auto w-full max-w-7xl animate-in fade-in duration-300 px-4 py-7 sm:px-6 lg:px-8", className)}
    {...props}
  >
    {children}
  </div>
));
ContentContainer.displayName = "ContentContainer";

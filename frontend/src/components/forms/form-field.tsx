import * as React from "react";

import { Label } from "@/components/ui/label";

export interface FormFieldProps {
  htmlFor: string;
  label: React.ReactNode;
  required?: boolean;
  error?: string;
  description?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

/**
 * FormField — the standard label + control + error/description block. Used
 * by every form in the app so field spacing/error styling stays consistent
 * instead of being hand-repeated per page.
 */
export function FormField({ htmlFor, label, required, error, description, className, children }: FormFieldProps) {
  return (
    <div className={className ?? "space-y-2"}>
      <Label htmlFor={htmlFor} required={required}>
        {label}
      </Label>
      {children}
      {error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : description ? (
        <p className="text-sm text-muted-foreground">{description}</p>
      ) : null}
    </div>
  );
}

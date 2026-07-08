import * as React from "react";
import { Controller, type Control, type FieldValues, type Path } from "react-hook-form";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export interface SwitchFieldProps<T extends FieldValues> {
  control: Control<T>;
  name: Path<T>;
  htmlFor: string;
  label: React.ReactNode;
  description?: React.ReactNode;
}

/** SwitchField — the standard bordered "active/inactive" toggle row used across every CRUD form. */
export function SwitchField<T extends FieldValues>({ control, name, htmlFor, label, description }: SwitchFieldProps<T>) {
  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <div className="space-y-0.5">
        <Label htmlFor={htmlFor}>{label}</Label>
        {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
      </div>
      <Controller control={control} name={name} render={({ field }) => <Switch id={htmlFor} checked={field.value} onCheckedChange={field.onChange} />} />
    </div>
  );
}

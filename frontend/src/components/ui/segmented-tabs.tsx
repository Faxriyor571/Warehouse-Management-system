import { cn } from "@/lib/utils";

export interface SegmentedTabOption<T extends string> {
  id: T;
  label: string;
}

export interface SegmentedTabsProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: SegmentedTabOption<T>[];
  className?: string;
}

export function SegmentedTabs<T extends string>({ value, onChange, options, className }: SegmentedTabsProps<T>) {
  return (
    <div className={cn("inline-flex rounded-lg border bg-muted/40 p-1", className)}>
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => onChange(option.id)}
          className={cn(
            "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            value === option.id ? "bg-card text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground"
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

"use client";

import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";
import { forwardRef, type SelectHTMLAttributes } from "react";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          "flex h-9 w-full appearance-none rounded border border-border bg-background px-3 pr-8 py-1 text-sm text-foreground",
          "transition-colors duration-100",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-foreground",
          "disabled:opacity-40 disabled:cursor-not-allowed",
          className
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        size={14}
        className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
      />
    </div>
  )
);
Select.displayName = "Select";

export { Select };

"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { forwardRef, type ButtonHTMLAttributes } from "react";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 font-medium transition-colors duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-40 select-none",
  {
    variants: {
      variant: {
        default:
          "bg-foreground text-background hover:bg-foreground/85 active:bg-foreground/75",
        outline:
          "border border-border bg-background text-foreground hover:bg-surface active:bg-muted",
        ghost:
          "text-foreground hover:bg-surface active:bg-muted",
        destructive:
          "bg-negative text-white hover:bg-negative/85 active:bg-negative/75",
        link:
          "text-foreground underline-offset-4 hover:underline p-0 h-auto",
      },
      size: {
        sm: "h-7 px-3 text-xs rounded-sm",
        default: "h-9 px-4 text-sm rounded",
        lg: "h-11 px-6 text-sm rounded-lg",
        icon: "h-9 w-9 rounded",
        "icon-sm": "h-7 w-7 rounded-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
);
Button.displayName = "Button";

export { Button, buttonVariants };

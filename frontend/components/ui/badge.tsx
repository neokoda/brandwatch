import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 font-medium rounded-full px-2 py-0.5 text-xs leading-none",
  {
    variants: {
      variant: {
        default: "bg-foreground text-background",
        outline: "border border-border text-foreground",
        muted: "bg-muted text-muted-foreground",
        positive: "chip-positive",
        negative: "chip-negative",
        neutral: "chip-neutral",
        warning: "chip-warning",
      },
    },
    defaultVariants: { variant: "muted" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };

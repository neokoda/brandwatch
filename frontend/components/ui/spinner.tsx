import { cn } from "@/lib/utils";

interface SpinnerProps {
  size?: "sm" | "default" | "lg";
  className?: string;
}

const sizeMap = {
  sm: "h-3 w-3 border",
  default: "h-4 w-4 border-[1.5px]",
  lg: "h-6 w-6 border-2",
};

function Spinner({ size = "default", className }: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn(
        "animate-spin rounded-full border-border border-t-foreground",
        sizeMap[size],
        className
      )}
    />
  );
}

export { Spinner };

import { cn } from "@/lib/utils";

interface StatProps {
  label: string;
  value: string | number;
  delta?: string;
  deltaPositive?: boolean;
  className?: string;
}

function Stat({ label, value, delta, deltaPositive, className }: StatProps) {
  return (
    <div className={cn("py-4", className)}>
      <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">{label}</p>
      <p className="text-2xl font-semibold tracking-tight">{value}</p>
      {delta && (
        <p
          className={cn(
            "mt-1 text-xs font-medium",
            deltaPositive ? "text-positive" : "text-negative"
          )}
        >
          {deltaPositive ? "+" : ""}{delta}
        </p>
      )}
    </div>
  );
}

export { Stat };

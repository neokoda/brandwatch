import { Badge } from "@/components/ui/badge";
import type { AlertSeverity } from "@/lib/types";

export function SeverityBadge({ severity }: { severity: AlertSeverity }) {
  const variant =
    severity === "critical" ? "negative" :
    severity === "warning" ? "warning" : "muted";
  return <Badge variant={variant}>{severity}</Badge>;
}

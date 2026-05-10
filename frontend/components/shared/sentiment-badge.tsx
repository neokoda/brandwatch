import { Badge } from "@/components/ui/badge";
import type { SentimentLabel } from "@/lib/types";

export function SentimentBadge({ label }: { label: SentimentLabel }) {
  const variant =
    label === "positive" ? "positive" :
    label === "negative" ? "negative" :
    label === "neutral" ? "neutral" : "muted";
  return <Badge variant={variant}>{label}</Badge>;
}

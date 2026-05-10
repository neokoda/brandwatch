import { Badge } from "@/components/ui/badge";
import type { SourceChannel } from "@/lib/types";

const labels: Record<SourceChannel, string> = {
  gdelt: "GDELT",
  youtube: "YouTube",
  reddit: "Reddit",
  rss: "RSS",
};

export function SourceBadge({ channel }: { channel: SourceChannel }) {
  return <Badge variant="muted">{labels[channel] ?? channel}</Badge>;
}

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { SentimentBadge } from "@/components/shared/sentiment-badge";
import { SourceBadge } from "@/components/shared/source-badge";
import { TrackerSelector } from "@/components/shared/tracker-selector";
import { mentionsApi, trackersApi } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { Mention, Tracker } from "@/lib/types";
import { Clock } from "lucide-react";

const PRIORITY_BADGE: Record<string, "negative" | "warning" | "muted" | "outline"> = {
  high: "negative",
  medium: "warning",
  low: "muted",
};

const PRIORITY_LABEL: Record<string, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

function slaMinutes(ingestedAt: string) {
  const mins = Math.floor((Date.now() - new Date(ingestedAt).getTime()) / 60_000);
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

const PRIORITY_ORDER = ["high", "medium", "low", "critical", ""];

export default function TriagePage() {
  const { user } = useAuth();
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("new");
  const [trackerId, setTrackerId] = useState("");
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    trackersApi.list().then(setTrackers).catch(console.error);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    mentionsApi.list({
      triage_status: status,
      tracker_id: trackerId || undefined,
      sentiment: "negative",
      page: 1,
      page_size: 50,
    }).then((res) => setMentions(res.items))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [status, trackerId]);

  useEffect(() => { load(); }, [load]);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { next.delete(id); } else { next.add(id); }
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === sorted.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(sorted.map((m) => m.id)));
    }
  }

  async function bulkUpdateStatus(newStatus: string) {
    await Promise.all(Array.from(selected).map((id) =>
      mentionsApi.triage(id, { triage_status: newStatus })
    ));
    setSelected(new Set());
    load();
  }

  const sorted = [...mentions].sort((a, b) => {
    const pa = PRIORITY_ORDER.indexOf(a.triage_priority ?? "");
    const pb = PRIORITY_ORDER.indexOf(b.triage_priority ?? "");
    return pa - pb;
  });

  return (
    <AppShell accountName={user?.account_name}>
      <PageHeader
        title="Triage"
        description="Priority queue for negative mentions"
      />

      <div className="mt-6 flex flex-wrap gap-3 items-center">
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-36">
          <option value="new">New</option>
          <option value="in_review">In review</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </Select>

        <TrackerSelector trackers={trackers} value={trackerId} onChange={setTrackerId} />

        {selected.size > 0 && (
          <div className="flex items-center gap-2 ml-2">
            <span className="text-sm text-muted-foreground">{selected.size} selected</span>
            <Button size="sm" variant="default" onClick={() => bulkUpdateStatus("in_review")}>Mark in review</Button>
            <Button size="sm" variant="default" onClick={() => bulkUpdateStatus("resolved")}>Mark resolved</Button>
            <Button size="sm" variant="ghost" onClick={() => bulkUpdateStatus("dismissed")}>Dismiss</Button>
            <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>Clear</Button>
          </div>
        )}
      </div>

      {/* Priority legend */}
      <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
        <span>Priority:</span>
        <span className="flex items-center gap-1"><Badge variant="negative">High</Badge> engagement &gt; 1</span>
        <span className="flex items-center gap-1"><Badge variant="warning">Medium</Badge> engagement &gt; 0</span>
        <span className="flex items-center gap-1"><Badge variant="muted">Low</Badge> no engagement</span>
      </div>

      <div className="mt-4">
        {loading ? (
          <div className="flex items-center gap-3 py-16 justify-center">
            <Spinner /> <span className="text-sm text-muted-foreground">Loading...</span>
          </div>
        ) : sorted.length === 0 ? (
          <div className="border border-border rounded-lg">
            <EmptyState title="Queue is clear" description="No negative mentions in this status." />
          </div>
        ) : (
          <div className="border border-border rounded-lg overflow-hidden">
            {/* Select-all header */}
            <div className="flex items-center gap-4 px-4 py-2 bg-surface border-b border-border text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={selected.size === sorted.length && sorted.length > 0}
                onChange={toggleAll}
              />
              <span>{sorted.length} mentions</span>
            </div>
            {sorted.map((m, i) => (
              <div
                key={m.id}
                className={`flex items-start gap-4 px-4 py-4 ${i !== 0 ? "border-t border-border" : ""} ${selected.has(m.id) ? "bg-muted/50" : "hover:bg-surface"}`}
              >
                <input
                  type="checkbox"
                  checked={selected.has(m.id)}
                  onChange={() => toggleSelect(m.id)}
                  className="mt-0.5 shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <SourceBadge channel={m.source_channel} />
                    <SentimentBadge label={m.sentiment_label} />
                    {m.triage_priority && PRIORITY_BADGE[m.triage_priority] && (
                      <Badge variant={PRIORITY_BADGE[m.triage_priority]}>
                        {PRIORITY_LABEL[m.triage_priority] ?? m.triage_priority}
                      </Badge>
                    )}
                    {m.is_influencer && <Badge variant="warning">Influencer</Badge>}
                    <span className="text-xs text-muted-foreground">{m.tracker_name}</span>
                  </div>
                  <Link href={`/mentions/${m.id}`} className="text-sm hover:underline line-clamp-2">
                    {m.content_excerpt || m.content_text.slice(0, 180)}
                  </Link>
                </div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                  <Clock size={11} />
                  <span>{slaMinutes(m.ingested_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

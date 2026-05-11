"use client";

import { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { insightsApi, trackersApi } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { CrossChannelInsight, Tracker } from "@/lib/types";
import { RefreshCw, Lightbulb } from "lucide-react";
import Link from "next/link";

export default function InsightsPage() {
  const { user } = useAuth();
  const [insights, setInsights] = useState<CrossChannelInsight[]>([]);
  const [trackerMap, setTrackerMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    Promise.all([insightsApi.list(), trackersApi.list()])
      .then(([i, ts]) => {
        setInsights(i);
        const map: Record<string, string> = {};
        ts.forEach((t: Tracker) => { map[t.id] = t.name; });
        setTrackerMap(map);
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleGenerate() {
    setGenerating(true);
    const before = Date.now();
    try {
      await insightsApi.generate(); // returns immediately (202 queued)
      // Poll until a new insight appears (generated after we queued) or 2-min timeout
      const deadline = Date.now() + 120_000;
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 3000));
        const updated = await insightsApi.list();
        const hasNew = updated.some(
          (i) => new Date(i.generated_at).getTime() > before
        );
        if (hasNew) {
          setInsights(updated);
          break;
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <AppShell accountName={user?.account_name}>
      <PageHeader
        title="Agent Insights"
        description="Cross-channel intelligence generated every 2 hours"
        action={
          <div className="flex items-center gap-3">
            {generating && <span className="text-xs text-muted-foreground animate-pulse">Generating insight…</span>}
            <Button size="sm" onClick={handleGenerate} disabled={generating}>
              {generating ? <Spinner /> : <Lightbulb size={13} />}
              Generate now
            </Button>
          </div>
        }
      />

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center gap-3 py-16 justify-center">
            <Spinner /> <span className="text-sm text-muted-foreground">Loading...</span>
          </div>
        ) : insights.length === 0 ? (
          <div className="border border-border rounded-lg">
            <EmptyState
              title="No insights yet"
              description="Cross-channel insights are generated when multiple trackers show concurrent elevated signals."
              action={
                <Button size="sm" variant="default" onClick={handleGenerate} disabled={generating}>
                  <RefreshCw size={13} /> Generate now
                </Button>
              }
            />
          </div>
        ) : (
          <div className="space-y-4">
            {insights.map((insight) => (
              <div key={insight.id} className="border border-border rounded-lg p-5">
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm leading-relaxed flex-1">{insight.insight_text}</p>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {insight.related_tracker_ids.map((tid) => (
                    <Link key={tid} href={`/mentions?tracker_id=${tid}`}>
                      <Badge variant="muted" className="cursor-pointer hover:bg-surface transition-colors">
                        {trackerMap[tid] ?? tid.slice(0, 8) + "…"}
                      </Badge>
                    </Link>
                  ))}
                  <span className="text-xs text-muted-foreground ml-auto">
                    {new Date(insight.generated_at).toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

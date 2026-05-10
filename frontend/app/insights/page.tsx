"use client";

import { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { insightsApi } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { CrossChannelInsight } from "@/lib/types";
import { RefreshCw, Lightbulb } from "lucide-react";

export default function InsightsPage() {
  const { user } = useAuth();
  const [insights, setInsights] = useState<CrossChannelInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    insightsApi.list().then(setInsights).finally(() => setLoading(false));
  }, []);

  async function handleGenerate() {
    setGenerating(true);
    await insightsApi.generate().catch(console.error);
    setTimeout(() => {
      insightsApi.list().then(setInsights);
      setGenerating(false);
    }, 4000);
  }

  return (
    <AppShell accountName={user?.account_name}>
      <PageHeader
        title="Agent Insights"
        description="Cross-channel intelligence generated every 2 hours"
        action={
          <Button size="sm" onClick={handleGenerate} disabled={generating}>
            {generating ? <Spinner /> : <Lightbulb size={13} />}
            Generate now
          </Button>
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
                <Button size="sm" variant="outline" onClick={handleGenerate} disabled={generating}>
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
                    <Badge key={tid} variant="muted">tracker: {tid.slice(0, 8)}…</Badge>
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

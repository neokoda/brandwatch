"use client";

import { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Stat } from "@/components/ui/stat";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { TrackerSelector } from "@/components/shared/tracker-selector";
import { TrendChart } from "@/components/shared/trend-chart";
import { SourceChart } from "@/components/shared/source-chart";
import { SeverityBadge } from "@/components/shared/severity-badge";
import { useAuth } from "@/components/providers/auth-provider";
import { analyticsApi, trackersApi, alertsApi, insightsApi } from "@/lib/api";
import type { KPIs, TrendPoint, SourceBreakdown, Alert, CrossChannelInsight, Tracker } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { RefreshCw, Lightbulb } from "lucide-react";

function fmtPct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

function fmtDelta(v: number | undefined): string | undefined {
  if (v == null) return undefined;
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}% vs prev period`;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [trackerId, setTrackerId] = useState("");
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [sources, setSources] = useState<SourceBreakdown[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [insights, setInsights] = useState<CrossChannelInsight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    trackersApi.list().then(setTrackers).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = trackerId ? { tracker_id: trackerId } : {};
    Promise.all([
      analyticsApi.kpis(params),
      analyticsApi.trends({ ...params, days: 14 }),
      analyticsApi.sources(params),
      alertsApi.list({ is_resolved: false }),
      insightsApi.list(),
    ])
      .then(([k, t, s, a, i]) => {
        setKpis(k);
        setTrends(t);
        setSources(s);
        setAlerts(a.slice(0, 5));
        setInsights(i.slice(0, 3));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [trackerId]);

  const [generating, setGenerating] = useState(false);
  async function handleGenerateInsight() {
    setGenerating(true);
    await insightsApi.generate().catch(console.error);
    setTimeout(() => {
      insightsApi.list().then((i) => setInsights(i.slice(0, 3)));
      setGenerating(false);
    }, 3000);
  }

  return (
    <AppShell accountName={user?.account_name}>
      <PageHeader
        title="Dashboard"
        description={user?.account_name}
        action={
          <TrackerSelector trackers={trackers} value={trackerId} onChange={setTrackerId} />
        }
      />

      {loading ? (
        <div className="flex items-center gap-3 py-16 justify-center">
          <Spinner /> <span className="text-sm text-muted-foreground">Loading...</span>
        </div>
      ) : (
        <div className="mt-6 space-y-8">
          {/* KPI row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-border border border-border rounded-lg">
            <Stat
              label="Total mentions"
              value={kpis?.total_mentions.toLocaleString() ?? "—"}
              delta={fmtDelta(kpis?.mentions_delta_pct)}
              deltaPositive={(kpis?.mentions_delta_pct ?? 0) >= 0}
              className="p-5"
            />
            <Stat
              label="Negative share"
              value={kpis ? fmtPct(kpis.negative_share) : "—"}
              delta={fmtDelta(kpis?.negative_delta_pct)}
              deltaPositive={(kpis?.negative_delta_pct ?? 0) <= 0}
              className="p-5"
            />
            <Stat
              label="Avg engagement"
              value={kpis?.avg_engagement.toFixed(2) ?? "—"}
              className="p-5"
            />
            <Stat
              label="Active alerts"
              value={kpis?.active_alerts ?? "—"}
              className="p-5"
            />
          </div>

          {/* Trend chart */}
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">Sentiment trend — last 14 days</p>
            {trends.length > 0 ? (
              <TrendChart data={trends} />
            ) : (
              <div className="border border-border rounded-lg">
                <EmptyState title="No trend data" description="Mentions will appear here once ingestion starts." />
              </div>
            )}
          </div>

          {/* Bottom grid: sources + alerts + insights */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Source breakdown */}
            <div className="lg:col-span-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">By source</p>
              {sources.length > 0 ? (
                <SourceChart data={sources} height={200} />
              ) : (
                <div className="border border-border rounded-lg">
                  <EmptyState title="No source data" />
                </div>
              )}
            </div>

            {/* Recent alerts */}
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">Recent alerts</p>
              {alerts.length > 0 ? (
                <div className="space-y-2">
                  {alerts.map((a) => (
                    <a key={a.id} href={`/alerts/${a.id}`} className="flex items-start gap-3 p-3 border border-border rounded hover:bg-surface transition-colors">
                      <SeverityBadge severity={a.severity} />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{a.title}</p>
                        <p className="text-xs text-muted-foreground">{a.tracker_name ?? "Cross-channel"}</p>
                      </div>
                    </a>
                  ))}
                </div>
              ) : (
                <div className="border border-border rounded-lg">
                  <EmptyState title="No active alerts" />
                </div>
              )}
            </div>

            {/* Cross-channel insights */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Agent insights</p>
                <Button size="icon-sm" variant="outline" onClick={handleGenerateInsight} disabled={generating}>
                  {generating ? <Spinner /> : <Lightbulb size={13} />}
                </Button>
              </div>
              {insights.length > 0 ? (
                <div className="space-y-3">
                  {insights.map((i) => (
                    <div key={i.id} className="p-3 border border-border rounded text-sm">
                      <p className="text-foreground leading-relaxed">{i.insight_text}</p>
                      <p className="text-xs text-muted-foreground mt-2">
                        {new Date(i.generated_at).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="border border-border rounded-lg">
                  <EmptyState
                    title="No insights yet"
                    description="Cross-channel insights are generated every 2 hours, or on demand."
                    action={
                      <Button size="sm" variant="outline" onClick={handleGenerateInsight} disabled={generating}>
                        <RefreshCw size={13} /> Generate now
                      </Button>
                    }
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

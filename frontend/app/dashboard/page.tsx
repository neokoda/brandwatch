"use client";

import { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Stat } from "@/components/ui/stat";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { TrackerSelector } from "@/components/shared/tracker-selector";
import { TrendChart } from "@/components/shared/trend-chart";
import { SourceChart } from "@/components/shared/source-chart";
import { SeverityBadge } from "@/components/shared/severity-badge";
import { useAuth } from "@/components/providers/auth-provider";
import { analyticsApi, trackersApi, alertsApi, insightsApi } from "@/lib/api";
import type { KPIs, TrendPoint, SourceBreakdown, Alert, CrossChannelInsight, Tracker, VelocityData } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { TrendingUp, TrendingDown, Minus, RefreshCw, Lightbulb, Plus, Zap, AlertTriangle } from "lucide-react";
import Link from "next/link";

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
  // null = trackers not yet loaded (suppress analytics fetch); "" = all trackers
  const [trackerId, setTrackerId] = useState<string | null>(null);
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [sources, setSources] = useState<SourceBreakdown[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [insights, setInsights] = useState<CrossChannelInsight[]>([]);
  const [velocity, setVelocity] = useState<VelocityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [trendDays, setTrendDays] = useState(14);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    trackersApi.list()
      .then((ts) => {
        setTrackers(ts);
        // Always set trackerId — "" means account-wide view, never leaves loading stuck
        setTrackerId(ts.length > 0 ? ts[0].id : "");
      })
      .catch(() => {
        // On failure still unblock the analytics effect
        setTrackerId("");
      });
  }, []);

  useEffect(() => {
    if (trackerId === null) return; // wait for trackers to load first
    setLoading(true);
    const params = trackerId ? { tracker_id: trackerId } : {};
    const granularity = trendDays <= 1 ? "hour" : "day";
    Promise.all([
      analyticsApi.kpis(params),
      analyticsApi.trends({ ...params, days: trendDays, granularity }),
      analyticsApi.sources(params),
      alertsApi.list({ is_resolved: false }),
      insightsApi.list(),
      analyticsApi.velocity(params).catch(() => null),
    ])
      .then(([k, t, s, a, i, v]) => {
        setKpis(k);
        setTrends(t);
        setSources(s);
        setAlerts(a.slice(0, 5));
        setInsights(i.slice(0, 3));
        setVelocity(v);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [trackerId, trendDays]);

  async function handleGenerateInsight() {
    setGenerating(true);
    await insightsApi.generate().catch(console.error);
    setTimeout(() => {
      insightsApi.list().then((i) => setInsights(i.slice(0, 3)));
      setGenerating(false);
    }, 3000);
  }

  const VelocityIcon = velocity?.trend === "up" ? TrendingUp : velocity?.trend === "down" ? TrendingDown : Minus;
  const velocityColor = velocity?.trend === "up" ? "text-positive" : velocity?.trend === "down" ? "text-negative" : "text-muted-foreground";

  return (
    <AppShell accountName={user?.account_name}>
      <PageHeader
        title="Dashboard"
        description={user?.account_name}
        action={
          <>
            <TrackerSelector trackers={trackers} value={trackerId ?? ""} onChange={setTrackerId} />
            <Link href="/settings">
              <Button><Plus size={14} /> Add tracker</Button>
            </Link>
          </>
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
              label="Positive share"
              value={kpis ? fmtPct(kpis.positive_share) : "—"}
              className="p-5"
            />
            <Stat
              label="Active alerts"
              value={kpis?.active_alerts ?? "—"}
              className="p-5"
            />
          </div>

          {/* Velocity + Anomaly signals */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Mention velocity */}
            <div className="border border-border rounded-lg p-5">
              <div className="flex items-center gap-2 mb-3">
                <Zap size={13} className="text-muted-foreground" />
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Mention velocity</p>
              </div>
              {velocity ? (
                <div className="space-y-2">
                  <div className="flex items-end gap-2">
                    <span className="text-2xl font-semibold tabular-nums">{velocity.last_24h_mentions}</span>
                    <span className="text-sm text-muted-foreground mb-0.5">mentions last 24h</span>
                    <VelocityIcon size={16} className={`mb-1 ${velocityColor}`} />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Now: <span className="text-foreground">{velocity.current_rate}</span>/hr &nbsp;·&nbsp;
                    Baseline: <span className="text-foreground">{velocity.baseline_rate}</span>/hr (~<span className="text-foreground">{velocity.mentions_per_day}</span>/day) &nbsp;·&nbsp;
                    <span className={velocity.velocity_ratio > 1.15 ? "text-warning" : "text-muted-foreground"}>
                      {velocity.velocity_ratio}× baseline
                    </span>
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No velocity data yet</p>
              )}
            </div>

            {/* Anomaly signals */}
            <div className="border border-border rounded-lg p-5">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={13} className="text-muted-foreground" />
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Anomaly signals</p>
              </div>
              {velocity ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${Math.abs(velocity.negativity_z) > 2.5 ? "bg-negative" : Math.abs(velocity.negativity_z) > 1.5 ? "bg-warning" : "bg-positive"}`} />
                    <span className="text-sm">
                      Negativity: <span className="font-medium">{fmtPct(velocity.current_negative_share)}</span>
                      <span className="text-muted-foreground ml-1">(z={velocity.negativity_z.toFixed(1)})</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${velocity.velocity_ratio > 3 ? "bg-negative" : velocity.velocity_ratio > 1.5 ? "bg-warning" : "bg-positive"}`} />
                    <span className="text-sm">
                      Volume: <span className="font-medium">{velocity.velocity_ratio}×</span> baseline
                      <span className="text-muted-foreground ml-1">{velocity.velocity_ratio > 1.15 ? "↑ elevated" : velocity.velocity_ratio < 0.85 ? "↓ low" : "normal"}</span>
                    </span>
                  </div>
                  {kpis && kpis.active_alerts > 0 && (
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-negative" />
                      <span className="text-sm">
                        <Link href="/alerts" className="underline">{kpis.active_alerts} active alert{kpis.active_alerts !== 1 ? "s" : ""}</Link>
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Anomaly signals computed per ingestion cycle</p>
              )}
            </div>
          </div>

          {/* Trend chart */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Sentiment trend</p>
              <div className="flex items-center gap-px border border-border rounded overflow-hidden">
                {([
                  { label: "24h", days: 1 },
                  { label: "7d", days: 7 },
                  { label: "14d", days: 14 },
                  { label: "30d", days: 30 },
                ] as const).map(({ label, days }) => (
                  <button
                    key={label}
                    onClick={() => setTrendDays(days)}
                    className={`px-3 py-1 text-xs transition-colors ${
                      trendDays === days
                        ? "bg-foreground text-background"
                        : "text-muted-foreground hover:text-foreground hover:bg-surface"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            {trends.length > 0 ? (
              <TrendChart data={trends} granularity={trendDays <= 1 ? "hour" : "day"} />
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
                <Button size="icon-sm" onClick={handleGenerateInsight} disabled={generating}>
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
                      <Button onClick={handleGenerateInsight} disabled={generating}>
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

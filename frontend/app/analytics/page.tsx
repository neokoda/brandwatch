"use client";

import { useState, useEffect, useRef } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { TrackerSelector } from "@/components/shared/tracker-selector";
import { TrendChart } from "@/components/shared/trend-chart";
import { SourceChart } from "@/components/shared/source-chart";
import { SourceBadge } from "@/components/shared/source-badge";
import { analyticsApi, trackersApi } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { TrendPoint, GeoPoint, SourceBreakdown, LanguageBreakdown, EmotionStat, AuthorStat, Tracker } from "@/lib/types";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, Cell,
} from "recharts";

const TABS = ["Trends", "Geographic", "Audience", "Emotions", "Channels", "Languages"] as const;
type Tab = typeof TABS[number];

const TREND_RANGES = [
  { label: "24h", days: 1, granularity: "hour" },
  { label: "7d", days: 7, granularity: "day" },
  { label: "30d", days: 30, granularity: "day" },
  { label: "90d", days: 90, granularity: "day" },
] as const;

export default function AnalyticsPage() {
  const { user } = useAuth();
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [trackerId, setTrackerId] = useState("");
  const [tab, setTab] = useState<Tab>("Trends");
  const [loading, setLoading] = useState(true);
  const [trendLoading, setTrendLoading] = useState(false);
  const trendInitialized = useRef(false);
  const [trendRange, setTrendRange] = useState<typeof TREND_RANGES[number]>(TREND_RANGES[1]);

  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [geo, setGeo] = useState<GeoPoint[]>([]);
  const [sources, setSources] = useState<SourceBreakdown[]>([]);
  const [languages, setLanguages] = useState<LanguageBreakdown[]>([]);
  const [emotions, setEmotions] = useState<EmotionStat[]>([]);
  const [authors, setAuthors] = useState<AuthorStat[]>([]);

  useEffect(() => {
    trackersApi.list().then(setTrackers).catch(console.error);
  }, []);

  // Full reload when tracker changes (includes trend + all other analytics)
  useEffect(() => {
    trendInitialized.current = false;
    const params = trackerId ? { tracker_id: trackerId } : {};
    setLoading(true);
    Promise.all([
      analyticsApi.trends({ ...params, days: trendRange.days, granularity: trendRange.granularity }),
      analyticsApi.geographic(params),
      analyticsApi.sources(params),
      analyticsApi.languages(params),
      analyticsApi.emotions(params),
      analyticsApi.authors(params),
    ]).then(([t, g, s, l, e, a]) => {
      setTrends(t); setGeo(g); setSources(s); setLanguages(l); setEmotions(e); setAuthors(a);
    }).catch(console.error).finally(() => {
      setLoading(false);
      trendInitialized.current = true;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackerId]); // trendRange intentionally excluded — handled by effect below

  // Trend-only refetch when time range changes (no full page reload)
  useEffect(() => {
    if (!trendInitialized.current) return;
    const params = trackerId ? { tracker_id: trackerId } : {};
    setTrendLoading(true);
    analyticsApi.trends({ ...params, days: trendRange.days, granularity: trendRange.granularity })
      .then(setTrends).catch(console.error).finally(() => setTrendLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trendRange]); // trackerId intentionally excluded — handled by effect above

  const tooltipStyle = {
    background: "var(--background)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    fontSize: 12,
  };

  // Emotion radar uses share * 100 so values fill the grid visibly
  const emotionData = emotions.map((e) => ({ ...e, pct: Math.round(e.share * 100) }));

  return (
    <AppShell accountName={user?.account_name}>
      <PageHeader
        title="Analytics"
        action={<TrackerSelector trackers={trackers} value={trackerId} onChange={setTrackerId} />}
      />

      {/* Tabs */}
      <div className="mt-6 border-b border-border flex gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm transition-colors border-b-2 -mb-px ${
              tab === t
                ? "border-foreground font-medium text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center gap-3 py-16 justify-center">
            <Spinner /> <span className="text-sm text-muted-foreground">Loading...</span>
          </div>
        ) : (
          <>
            {tab === "Trends" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Sentiment over time</p>
                  <div className="flex items-center gap-px border border-border rounded overflow-hidden">
                    {TREND_RANGES.map((r) => (
                      <button
                        key={r.label}
                        onClick={() => setTrendRange(r)}
                        className={`px-3 py-1 text-xs transition-colors ${
                          trendRange.label === r.label
                            ? "bg-foreground text-background"
                            : "text-muted-foreground hover:text-foreground hover:bg-surface"
                        }`}
                      >
                        {r.label}
                      </button>
                    ))}
                  </div>
                </div>
                {trendLoading ? (
                  <div className="flex items-center gap-3 py-16 justify-center border border-border rounded-lg">
                    <Spinner /> <span className="text-sm text-muted-foreground">Loading...</span>
                  </div>
                ) : trends.length > 0 ? <TrendChart data={trends} height={320} granularity={trendRange.granularity} /> : <Empty />}
              </div>
            )}

            {tab === "Geographic" && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">Mentions by region (top 20)</p>
                {geo.length > 0 ? (
                  <ResponsiveContainer width="100%" height={Math.max(240, geo.slice(0, 20).length * 28)}>
                    <BarChart data={geo.slice(0, 20)} layout="vertical" margin={{ left: 20, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis type="number" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
                      <YAxis type="category" dataKey="region_code" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} width={40} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="mention_count" name="Mentions" radius={[0, 2, 2, 0]}>
                        {geo.slice(0, 20).map((entry) => (
                          <Cell
                            key={entry.region_code}
                            fill={entry.negative_share > 0.5 ? "var(--negative)" : entry.negative_share > 0.3 ? "var(--warning)" : "var(--foreground)"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : <Empty />}
              </div>
            )}

            {tab === "Audience" && (
              <div className="space-y-6">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Top authors by mention count</p>
                {authors.length > 0 ? (
                  <div className="border border-border rounded-lg overflow-hidden">
                    {authors.slice(0, 15).map((a, i) => (
                      <div key={a.author_name} className={`flex items-center gap-4 px-4 py-3 text-sm ${i !== 0 ? "border-t border-border" : ""}`}>
                        <span className="w-5 text-muted-foreground text-xs">{i + 1}</span>
                        <span className="flex-1 font-medium truncate">{a.author_name}</span>
                        {a.top_channel && <SourceBadge channel={a.top_channel as never} />}
                        {a.is_influencer && <Badge variant="warning">Influencer</Badge>}
                        <span className="text-muted-foreground">{a.mention_count} mentions</span>
                      </div>
                    ))}
                  </div>
                ) : <Empty />}
              </div>
            )}

            {tab === "Emotions" && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">Emotion distribution (English, negative mentions)</p>
                {emotionData.length > 0 ? (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
                    <ResponsiveContainer width="100%" height={340}>
                      <RadarChart data={emotionData} outerRadius="75%">
                        <PolarGrid stroke="var(--border)" />
                        <PolarAngleAxis dataKey="emotion_label" tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} />
                        <Radar
                          dataKey="pct"
                          fill="var(--foreground)"
                          fillOpacity={0.2}
                          stroke="var(--foreground)"
                          strokeWidth={2}
                          dot={{ r: 3, fill: "var(--foreground)" }}
                        />
                        <Tooltip
                          contentStyle={tooltipStyle}
                          formatter={(v) => [`${Number(v ?? 0).toFixed(1)}%`, "Share"]}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                    <div className="space-y-3">
                      {emotionData.map((e) => (
                        <div key={e.emotion_label} className="flex items-center gap-3">
                          <span className="w-20 text-sm text-muted-foreground capitalize">{e.emotion_label}</span>
                          <div className="flex-1 bg-muted rounded-full h-2">
                            <div
                              className="bg-foreground h-2 rounded-full transition-all"
                              style={{ width: `${e.pct}%` }}
                            />
                          </div>
                          <span className="text-xs tabular-nums text-muted-foreground w-10 text-right">{e.pct}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <EmptyState title="No emotion data" description="Emotion detection runs on English negative mentions only." />
                )}
              </div>
            )}

            {tab === "Channels" && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">Mentions by source channel</p>
                {sources.length > 0 ? <SourceChart data={sources} height={300} /> : <Empty />}
              </div>
            )}

            {tab === "Languages" && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">Language distribution</p>
                {languages.length > 0 ? (
                  <div className="border border-border rounded-lg overflow-hidden">
                    {languages.slice(0, 15).map((l, i) => (
                      <div key={l.language_code} className={`flex items-center gap-4 px-4 py-3 text-sm ${i !== 0 ? "border-t border-border" : ""}`}>
                        <Badge variant="outline">{l.language_code}</Badge>
                        <div className="flex-1 flex gap-0.5 h-2 rounded-full overflow-hidden bg-muted">
                          <div
                            className="h-full bg-positive transition-all"
                            style={{ width: `${(l.positive_share * 100).toFixed(0)}%` }}
                            title={`Positive: ${(l.positive_share * 100).toFixed(0)}%`}
                          />
                          <div
                            className="h-full bg-negative transition-all"
                            style={{ width: `${(l.negative_share * 100).toFixed(0)}%` }}
                            title={`Negative: ${(l.negative_share * 100).toFixed(0)}%`}
                          />
                        </div>
                        <span className="text-muted-foreground">{l.mention_count.toLocaleString()}</span>
                        <span className="text-positive text-xs w-16 text-right">{(l.positive_share * 100).toFixed(0)}% pos</span>
                        <span className="text-negative text-xs w-16 text-right">{(l.negative_share * 100).toFixed(0)}% neg</span>
                      </div>
                    ))}
                  </div>
                ) : <Empty />}
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}

function Empty() {
  return (
    <div className="border border-border rounded-lg">
      <EmptyState title="No data available" description="Data will appear once mentions are ingested." />
    </div>
  );
}

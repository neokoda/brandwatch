"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { SentimentBadge } from "@/components/shared/sentiment-badge";
import { SourceBadge } from "@/components/shared/source-badge";
import { TrackerSelector } from "@/components/shared/tracker-selector";
import { useMentionStream } from "@/lib/sse";
import { mentionsApi, trackersApi, exportApi, filtersApi } from "@/lib/api";
import type { SavedFilter } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { Mention, Tracker } from "@/lib/types";
import { Download, Search, RefreshCw, Bookmark, BookmarkCheck, ChevronDown } from "lucide-react";
import { getToken } from "@/lib/auth";

function fmtTime(iso: string) {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return d.toLocaleDateString();
}

export default function MentionsPage() {
  const { user } = useAuth();
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [trackerId, setTrackerId] = useState("");
  const [sentiment, setSentiment] = useState("");
  const [source, setSource] = useState("");
  const [search, setSearch] = useState("");
  const [language, setLanguage] = useState("");
  const [region, setRegion] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [liveCount, setLiveCount] = useState(0);

  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([]);
  const [filterName, setFilterName] = useState("");
  const [showSaveInput, setShowSaveInput] = useState(false);
  const [savingFilter, setSavingFilter] = useState(false);
  const [showFiltersDropdown, setShowFiltersDropdown] = useState(false);

  useEffect(() => {
    trackersApi.list().then(setTrackers).catch(console.error);
    filtersApi.list().then(setSavedFilters).catch(console.error);
  }, []);

  const load = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const res = await mentionsApi.list({
        tracker_id: trackerId || undefined,
        sentiment: sentiment || undefined,
        source: source || undefined,
        search: search || undefined,
        language: language || undefined,
        region: region || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page: p,
        page_size: 25,
      });
      setMentions(res.items);
      setTotal(res.total);
      setPage(p);
    } finally {
      setLoading(false);
    }
  }, [trackerId, sentiment, source, search, language, region, dateFrom, dateTo]);

  useEffect(() => {
    load(1);
    setLiveCount(0);
  }, [load]);

  useMentionStream(
    () => setLiveCount((c) => c + 1),
    trackerId || undefined
  );

  const token = getToken();
  const exportUrl = exportApi.mentionsCsvUrl({
    tracker_id: trackerId || undefined,
    sentiment: sentiment || undefined,
    source: source || undefined,
    search: search || undefined,
    language: language || undefined,
    region: region || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    token: token ?? undefined,
  });

  async function saveFilter() {
    if (!filterName.trim()) return;
    setSavingFilter(true);
    try {
      const params: Record<string, string | number | boolean> = {};
      if (trackerId) params.tracker_id = trackerId;
      if (sentiment) params.sentiment = sentiment;
      if (source) params.source = source;
      if (search) params.search = search;
      if (language) params.language = language;
      if (region) params.region = region;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const saved = await filtersApi.create({ name: filterName.trim(), tracker_id: trackerId || undefined, filter_params: params });
      setSavedFilters((prev) => [...prev, saved]);
      setFilterName("");
      setShowSaveInput(false);
    } catch {
      /* noop */
    } finally {
      setSavingFilter(false);
    }
  }

  function applyFilter(f: SavedFilter) {
    const p = f.filter_params;
    setTrackerId((p.tracker_id as string) ?? "");
    setSentiment((p.sentiment as string) ?? "");
    setSource((p.source as string) ?? "");
    setSearch((p.search as string) ?? "");
    setLanguage((p.language as string) ?? "");
    setRegion((p.region as string) ?? "");
    setDateFrom((p.date_from as string) ?? "");
    setDateTo((p.date_to as string) ?? "");
  }

  async function deleteFilter(id: string) {
    await filtersApi.delete(id);
    setSavedFilters((prev) => prev.filter((f) => f.id !== id));
  }

  return (
    <AppShell accountName={user?.account_name}>
      <PageHeader
        title="Mentions"
        description={`${total.toLocaleString()} total`}
        action={
          <div className="flex items-center gap-2">
            {liveCount > 0 && (
              <button
                onClick={() => { load(1); setLiveCount(0); }}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-foreground text-background rounded-full font-medium animate-fade-in"
              >
                <span className="w-1.5 h-1.5 bg-background rounded-full" />
                {liveCount} new
              </button>
            )}
            <a href={exportUrl} target="_blank" rel="noreferrer">
              <Button size="sm" variant="default"><Download size={13} /> Export CSV</Button>
            </a>
          </div>
        }
      />

      {/* Filters */}
      <div className="mt-6 space-y-3">
        <div className="flex flex-wrap gap-3">
          <TrackerSelector trackers={trackers} value={trackerId} onChange={setTrackerId} />
          <Select value={sentiment} onChange={(e) => setSentiment(e.target.value)} className="w-40">
            <option value="">All sentiments</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
            <option value="neutral">Neutral</option>
          </Select>
          <Select value={source} onChange={(e) => setSource(e.target.value)} className="w-40">
            <option value="">All sources</option>
            <option value="gdelt">News (GDELT)</option>
            <option value="youtube">YouTube</option>
            <option value="rss">RSS</option>
            <option value="hackernews">Hacker News</option>
            <option value="playstore">Play Store</option>
            <option value="appstore">App Store</option>
            <option value="reddit">Reddit</option>
            <option value="bluesky">Bluesky</option>
            <option value="mastodon">Mastodon</option>
          </Select>
          <div className="relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-8 w-52"
              placeholder="Search mentions..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button variant="ghost" onClick={() => setShowAdvanced((v) => !v)} className="text-muted-foreground text-sm">
            {showAdvanced ? "Less filters" : "More filters"}
          </Button>
          <Button size="icon" variant="default" onClick={() => load(1)} title="Refresh">
            <RefreshCw size={14} />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowSaveInput((v) => !v)}
            className="text-muted-foreground gap-1.5"
            title="Save current filters"
          >
            {showSaveInput ? <BookmarkCheck size={13} /> : <Bookmark size={13} />}
            Save filter
          </Button>
          {savedFilters.length > 0 && (
            <div className="relative">
              <Button
                size="sm"
                variant="ghost"
                className="text-muted-foreground gap-1.5"
                onClick={() => setShowFiltersDropdown((v) => !v)}
              >
                <ChevronDown size={13} /> Saved filters
              </Button>
              {showFiltersDropdown && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowFiltersDropdown(false)} />
                  <div className="absolute left-0 top-full mt-1 z-20 min-w-[180px] bg-background border border-border rounded-lg shadow-lg py-1">
                    {savedFilters.map((f) => (
                      <div key={f.id} className="flex items-center justify-between px-3 py-1.5 hover:bg-muted cursor-pointer text-sm">
                        <span
                          onClick={() => { applyFilter(f); setShowFiltersDropdown(false); }}
                          className="flex-1 truncate"
                        >{f.name}</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteFilter(f.id); }}
                          className="text-muted-foreground hover:text-destructive ml-2 text-xs"
                        >✕</button>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {showSaveInput && (
          <div className="flex items-center gap-2 pt-1">
            <Input
              className="w-52"
              placeholder="Filter name…"
              value={filterName}
              onChange={(e) => setFilterName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveFilter()}
            />
            <Button size="sm" onClick={saveFilter} disabled={savingFilter || !filterName.trim()}>
              {savingFilter ? <Spinner /> : "Save"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => { setShowSaveInput(false); setFilterName(""); }}>
              Cancel
            </Button>
          </div>
        )}

        {showAdvanced && (
          <div className="flex flex-wrap gap-3 pt-1">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Language code</label>
              <Input className="w-32" placeholder="en, fr, de…" value={language} onChange={(e) => setLanguage(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Region code</label>
              <Input className="w-32" placeholder="US, GB, AU…" value={region} onChange={(e) => setRegion(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Published from</label>
              <Input type="date" className="w-40" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Published to</label>
              <Input type="date" className="w-40" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </div>
            {(language || region || dateFrom || dateTo) && (
              <div className="flex items-end">
                <Button variant="ghost" className="text-muted-foreground"
                  onClick={() => { setLanguage(""); setRegion(""); setDateFrom(""); setDateTo(""); }}>
                  Clear
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center gap-3 justify-center py-16">
            <Spinner /> <span className="text-sm text-muted-foreground">Loading mentions...</span>
          </div>
        ) : mentions.length === 0 ? (
          <div className="border border-border rounded-lg">
            <EmptyState
              title="No mentions found"
              description="Adjust filters or wait for the next ingestion cycle."
            />
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead>Content</TableHead>
                  <TableHead>Sentiment</TableHead>
                  <TableHead>Tracker</TableHead>
                  <TableHead>Engagement</TableHead>
                  <TableHead>Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mentions.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell><SourceBadge channel={m.source_channel} /></TableCell>
                    <TableCell className="max-w-sm">
                      <Link href={`/mentions/${m.id}`} className="hover:underline text-foreground line-clamp-2">
                        {m.content_excerpt || m.content_text.slice(0, 140)}
                      </Link>
                      {m.is_influencer && (
                        <Badge variant="warning" className="mt-1">Influencer</Badge>
                      )}
                    </TableCell>
                    <TableCell><SentimentBadge label={m.sentiment_label} /></TableCell>
                    <TableCell className="text-muted-foreground text-xs">{m.tracker_name}</TableCell>
                    <TableCell className="text-muted-foreground tabular-nums">
                      {(m.source_channel === "gdelt" || m.source_channel === "rss") ? "—" : m.engagement_score.toFixed(1)}
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap">{fmtTime(m.ingested_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-4 text-sm text-muted-foreground">
              <span>Showing {((page - 1) * 25) + 1}–{Math.min(page * 25, total)} of {total.toLocaleString()}</span>
              <div className="flex gap-1">
                <Button size="sm" variant="default" disabled={page === 1} onClick={() => load(1)} title="First page">«</Button>
                <Button size="sm" variant="default" disabled={page === 1} onClick={() => load(page - 1)}>Previous</Button>
                <Button size="sm" variant="default" disabled={page * 25 >= total} onClick={() => load(page + 1)}>Next</Button>
                <Button size="sm" variant="default" disabled={page * 25 >= total} onClick={() => load(Math.ceil(total / 25))} title="Last page">»</Button>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

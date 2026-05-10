"use client";

import { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { Separator } from "@/components/ui/separator";
import { trackersApi, accountApi, ingestApi } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { Tracker, Account, IngestionRun } from "@/lib/types";
import { Plus, Trash2, RefreshCw, Save } from "lucide-react";

const TABS = ["Trackers", "Agent", "Ingestion"] as const;
type Tab = typeof TABS[number];

export default function SettingsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("Trackers");

  return (
    <AppShell accountName={user?.account_name}>
      <PageHeader title="Settings" />

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
        {tab === "Trackers" && <TrackersTab />}
        {tab === "Agent" && <AgentTab />}
        {tab === "Ingestion" && <IngestionTab />}
      </div>
    </AppShell>
  );
}

const ALL_SOURCES = ["gdelt", "youtube", "reddit", "rss", "hackernews", "bluesky", "mastodon", "playstore", "appstore"] as const;
type SourceKey = typeof ALL_SOURCES[number];

const SOURCE_LABELS: Record<SourceKey, string> = {
  gdelt: "News (GDELT)",
  youtube: "YouTube",
  reddit: "Reddit",
  rss: "RSS",
  hackernews: "Hacker News",
  bluesky: "Bluesky",
  mastodon: "Mastodon",
  playstore: "Play Store",
  appstore: "App Store",
};

const RSS_SUGGESTIONS = [
  { label: "Medium (technology)", url: "https://medium.com/feed/tag/technology" },
  { label: "TechCrunch", url: "https://techcrunch.com/feed/" },
  { label: "Wired", url: "https://www.wired.com/feed/rss" },
  { label: "The Verge", url: "https://www.theverge.com/rss/index.xml" },
  { label: "Substack (tech)", url: "https://substack.com/feed/tag/technology" },
];

function TrackersTab() {
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newKeywords, setNewKeywords] = useState("");
  const [newSources, setNewSources] = useState<SourceKey[]>([]);
  const [newRssFeeds, setNewRssFeeds] = useState<string[]>([]);
  const [rssInput, setRssInput] = useState("");
  const [refreshing, setRefreshing] = useState<string | null>(null);

  const rssActive = newSources.length === 0 || newSources.includes("rss");

  useEffect(() => {
    trackersApi.list().then(setTrackers).finally(() => setLoading(false));
  }, []);

  function toggleSource(s: SourceKey) {
    setNewSources((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  }

  function addRssFeed(url: string) {
    const trimmed = url.trim();
    if (trimmed && !newRssFeeds.includes(trimmed)) {
      setNewRssFeeds((prev) => [...prev, trimmed]);
    }
    setRssInput("");
  }

  async function handleCreate() {
    if (!newName.trim()) return;
    setCreating(true);
    const tracker = await trackersApi.create({
      name: newName,
      tracker_type: "brand",
      keywords: newKeywords.split(",").map((k) => k.trim()).filter(Boolean),
      sources: newSources,
      rss_feeds: newRssFeeds,
    });
    setTrackers((prev) => [...prev, tracker]);
    setNewName(""); setNewKeywords(""); setNewSources([]); setNewRssFeeds([]); setRssInput("");
    setCreating(false);
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this tracker? All its mentions will be deleted.")) return;
    await trackersApi.delete(id);
    setTrackers((prev) => prev.filter((t) => t.id !== id));
  }

  async function handleRefresh(id: string) {
    setRefreshing(id);
    await trackersApi.refresh(id).catch(console.error);
    setTimeout(() => setRefreshing(null), 2000);
  }

  async function toggleActive(tracker: Tracker) {
    const updated = await trackersApi.update(tracker.id, { is_active: !tracker.is_active });
    setTrackers((prev) => prev.map((t) => t.id === tracker.id ? updated : t));
  }

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Create new tracker */}
      <div className="border border-border rounded-lg p-5 space-y-4">
        <p className="text-sm font-medium">Add tracker</p>
        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Name</label>
          <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. McDonald's Brand" />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Keywords (comma-separated)</label>
          <Input value={newKeywords} onChange={(e) => setNewKeywords(e.target.value)} placeholder="McDonald's, BigMac, McFlurry" />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">
            Sources
            <span className="ml-1 normal-case font-normal text-muted-foreground">(leave all unchecked to enable all)</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {ALL_SOURCES.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => toggleSource(s)}
                className={`px-2.5 py-1 rounded text-xs border transition-colors ${
                  newSources.includes(s)
                    ? "bg-foreground text-background border-foreground"
                    : "border-border text-muted-foreground hover:text-foreground hover:border-foreground"
                }`}
              >
                {SOURCE_LABELS[s]}
              </button>
            ))}
          </div>
        </div>
        {rssActive && (
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">
              RSS feeds
              <span className="ml-1 normal-case font-normal">— blogs, newsletters, niche news</span>
            </label>
            <div className="flex gap-2">
              <Input
                value={rssInput}
                onChange={(e) => setRssInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addRssFeed(rssInput))}
                placeholder="https://example.com/feed/"
                className="flex-1"
              />
              <Button variant="default" onClick={() => addRssFeed(rssInput)} disabled={!rssInput.trim()}>
                Add
              </Button>
            </div>
            {newRssFeeds.length > 0 && (
              <div className="flex flex-col gap-1">
                {newRssFeeds.map((url) => (
                  <div key={url} className="flex items-center justify-between gap-2 px-3 py-1.5 border border-border rounded text-xs text-foreground">
                    <span className="truncate font-mono">{url}</span>
                    <button onClick={() => setNewRssFeeds((p) => p.filter((u) => u !== url))} className="text-muted-foreground hover:text-foreground shrink-0">✕</button>
                  </div>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              <span className="text-xs text-muted-foreground">Suggested:</span>
              {RSS_SUGGESTIONS.filter((s) => !newRssFeeds.includes(s.url)).map((s) => (
                <button
                  key={s.url}
                  onClick={() => addRssFeed(s.url)}
                  className="text-xs px-2 py-0.5 rounded border border-border text-muted-foreground hover:text-foreground hover:border-foreground transition-colors"
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}
        <Button variant="default" onClick={handleCreate} disabled={creating || !newName.trim()}>
          {creating ? <Spinner /> : <Plus size={13} />}
          Add tracker
        </Button>
      </div>

      {/* Existing trackers */}
      {trackers.length === 0 ? (
        <EmptyState title="No trackers yet" />
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          {trackers.map((t, i) => (
            <div key={t.id} className={`flex items-center gap-4 px-4 py-4 ${i !== 0 ? "border-t border-border" : ""}`}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{t.name}</span>
                  {!t.is_active && <Badge variant="muted">Inactive</Badge>}
                  {t.rss_feeds?.length > 0 && (
                    <span className="text-xs text-muted-foreground">{t.rss_feeds.length} RSS feed{t.rss_feeds.length > 1 ? "s" : ""}</span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {t.keywords.slice(0, 5).map((k) => (
                    <span key={k} className="text-xs text-muted-foreground">{k}</span>
                  ))}
                  {t.keywords.length > 5 && <span className="text-xs text-muted-foreground">+{t.keywords.length - 5}</span>}
                </div>
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {(t.sources?.length ? t.sources : ALL_SOURCES).map((s) => (
                    <span key={s} className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{SOURCE_LABELS[s as SourceKey] ?? s}</span>
                  ))}
                  {!t.sources?.length && <span className="text-xs text-muted-foreground ml-0.5">(all)</span>}
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button size="icon-sm" variant="ghost" onClick={() => handleRefresh(t.id)} title="Trigger ingestion">
                  {refreshing === t.id ? <Spinner /> : <RefreshCw size={13} />}
                </Button>
                <Button size="icon-sm" variant="ghost" onClick={() => toggleActive(t)} title={t.is_active ? "Deactivate" : "Activate"}>
                  <span className={`w-2 h-2 rounded-full ${t.is_active ? "bg-positive" : "bg-muted-foreground"}`} />
                </Button>
                <Button size="icon-sm" variant="ghost" onClick={() => handleDelete(t.id)} title="Delete">
                  <Trash2 size={13} />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AgentTab() {
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");

  useEffect(() => {
    accountApi.get().then((a) => {
      setAccount(a);
      setWebhookUrl(a.agent_webhook_url ?? "");
      setTelegramChatId(a.telegram_chat_id ?? "");
    }).finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    const updated = await accountApi.update({
      agent_webhook_url: webhookUrl || undefined,
      agent_api_token: apiToken || undefined,
      telegram_chat_id: telegramChatId || undefined,
    });
    setAccount(updated);
    setApiToken("");
    setSaving(false);
  }

  if (loading) return <Spinner />;

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <p className="text-sm font-medium mb-1">BYOA — Bring Your Own Agent</p>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Configure your own OpenAI-compatible agent endpoint. When alerts fire, the platform POSTs a structured payload to this webhook. You can use Hermes, OpenClaw, or any compatible agent.
        </p>
      </div>

      <Separator />

      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Agent webhook URL</label>
          <Input
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://your-agent.com/v1/chat/completions"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">API token (leave blank to keep current)</label>
          <Input
            type="password"
            value={apiToken}
            onChange={(e) => setApiToken(e.target.value)}
            placeholder="sk-..."
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Telegram chat ID (for notifications)</label>
          <Input
            value={telegramChatId}
            onChange={(e) => setTelegramChatId(e.target.value)}
            placeholder="-100123456789"
          />
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? <Spinner /> : <Save size={13} />}
          Save agent config
        </Button>
      </div>

      {account?.agent_webhook_url && (
        <div className="border border-border rounded-lg p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-2">Current endpoint</p>
          <p className="text-sm font-mono break-all">{account.agent_webhook_url}</p>
        </div>
      )}
    </div>
  );
}

function IngestionTab() {
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ingestApi.runs().then(setRuns).finally(() => setLoading(false));
  }, []);

  function fmtDt(iso?: string) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString();
  }

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">Last 20 ingestion runs across all trackers.</p>
      {runs.length === 0 ? (
        <EmptyState title="No runs yet" description="Ingestion runs every 15–30 minutes per source." />
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          {runs.map((r, i) => (
            <div key={r.id} className={`flex items-center gap-4 px-4 py-3 text-sm ${i !== 0 ? "border-t border-border" : ""}`}>
              <Badge variant="muted">{r.source.toUpperCase()}</Badge>
              <Badge variant={r.status === "success" ? "positive" : r.status === "failed" ? "negative" : "muted"}>
                {r.status}
              </Badge>
              <span className="text-muted-foreground flex-1 truncate">{fmtDt(r.started_at)}</span>
              <span className="text-muted-foreground">{r.mentions_stored} stored / {r.mentions_found} found</span>
              {r.error_message && (
                <span className="text-negative text-xs truncate max-w-xs" title={r.error_message}>{r.error_message}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

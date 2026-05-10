"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import { SentimentBadge } from "@/components/shared/sentiment-badge";
import { SourceBadge } from "@/components/shared/source-badge";
import { mentionsApi } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { Mention } from "@/lib/types";
import { ArrowLeft, ExternalLink } from "lucide-react";

function fmtDt(iso: string) {
  return new Date(iso).toLocaleString();
}

export default function MentionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [mention, setMention] = useState<Mention | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [triageStatus, setTriageStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [assignee, setAssignee] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    mentionsApi.get(id).then((m) => {
      setMention(m);
      setTriageStatus(m.triage_status);
      setPriority(m.triage_priority ?? "");
      setAssignee(m.triage_assignee ?? "");
      setNote(m.triage_note ?? "");
    }).finally(() => setLoading(false));
  }, [id]);

  async function saveTriage() {
    if (!mention) return;
    setSaving(true);
    try {
      const updated = await mentionsApi.triage(id, {
        triage_status: triageStatus || undefined,
        triage_priority: priority || undefined,
        triage_assignee: assignee || undefined,
        triage_note: note || undefined,
      });
      setMention(updated);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <AppShell accountName={user?.account_name}>
        <div className="flex items-center gap-3 py-16 justify-center">
          <Spinner /> <span className="text-sm text-muted-foreground">Loading...</span>
        </div>
      </AppShell>
    );
  }

  if (!mention) return null;

  return (
    <AppShell accountName={user?.account_name}>
      <div className="pb-6 border-b border-border flex items-center gap-3">
        <Button size="icon-sm" variant="ghost" onClick={() => router.back()}>
          <ArrowLeft size={15} />
        </Button>
        <div className="flex items-center gap-2 flex-wrap">
          <SourceBadge channel={mention.source_channel} />
          <SentimentBadge label={mention.sentiment_label} />
          {mention.is_influencer && <Badge variant="warning">Influencer</Badge>}
          {mention.emotion_label && <Badge variant="muted">{mention.emotion_label}</Badge>}
          {mention.topic_label && <Badge variant="outline">{mention.topic_label}</Badge>}
        </div>
        <a
          href={mention.source_url}
          target="_blank"
          rel="noreferrer"
          className="ml-auto"
        >
          <Button size="sm" variant="outline"><ExternalLink size={13} /> Source</Button>
        </a>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Content */}
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">Content</p>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{mention.content_text}</p>
          </div>

          <Separator />

          {/* Metadata grid */}
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">Metadata</p>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <MetaRow label="Author" value={mention.author_name ?? "—"} />
              <MetaRow label="Source" value={mention.source_domain ?? "—"} />
              <MetaRow label="Language" value={mention.language_code ?? "—"} />
              <MetaRow label="Region" value={mention.region_code ?? "—"} />
              <MetaRow label="Engagement" value={mention.engagement_score.toFixed(2)} />
              <MetaRow label="Sentiment score" value={mention.sentiment_score.toFixed(3)} />
              <MetaRow label="Published" value={mention.published_at ? fmtDt(mention.published_at) : "—"} />
              <MetaRow label="Ingested" value={fmtDt(mention.ingested_at)} />
              <MetaRow label="Tracker" value={mention.tracker_name ?? "—"} />
              {mention.keywords_matched.length > 0 && (
                <div className="col-span-2">
                  <dt className="text-muted-foreground">Keywords matched</dt>
                  <dd className="flex flex-wrap gap-1 mt-1">
                    {mention.keywords_matched.map((k) => (
                      <Badge key={k} variant="muted">{k}</Badge>
                    ))}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>

        {/* Triage panel */}
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">Triage</p>
          <div className="border border-border rounded-lg p-4 space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Status</label>
              <Select value={triageStatus} onChange={(e) => setTriageStatus(e.target.value)}>
                <option value="new">New</option>
                <option value="in_review">In review</option>
                <option value="resolved">Resolved</option>
                <option value="dismissed">Dismissed</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Priority</label>
              <Select value={priority} onChange={(e) => setPriority(e.target.value)}>
                <option value="">None</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Assignee</label>
              <Input
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
                placeholder="email or name"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Note</label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Add a note..."
                rows={3}
                className="w-full border border-border rounded px-3 py-2 text-sm resize-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring bg-background"
              />
            </div>
            <Button className="w-full" onClick={saveTriage} disabled={saving}>
              {saving ? <Spinner /> : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium mt-0.5">{value}</dd>
    </div>
  );
}

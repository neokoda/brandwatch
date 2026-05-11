"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import { SeverityBadge } from "@/components/shared/severity-badge";
import { alertsApi } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { Alert } from "@/lib/types";
import { ArrowLeft, CheckCircle, Zap } from "lucide-react";

export default function AlertDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [alert, setAlert] = useState<Alert | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(false);
  const [drafting, setDrafting] = useState(false);

  useEffect(() => {
    alertsApi.get(id).then(setAlert).finally(() => setLoading(false));
  }, [id]);

  async function handleResolve() {
    setResolving(true);
    const updated = await alertsApi.resolve(id);
    setAlert(updated);
    setResolving(false);
  }

  async function handleDraft() {
    setDrafting(true);
    try {
      const res = await alertsApi.draftResponse(id);
      setAlert((prev) => prev ? { ...prev, draft_response: res.draft_response ?? undefined, agent_notified: true } : prev);
    } finally {
      setDrafting(false);
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

  if (!alert) return null;

  return (
    <AppShell accountName={user?.account_name}>
      <div className="pb-6 border-b border-border flex items-center gap-3">
        <Button size="icon-sm" variant="ghost" onClick={() => router.back()}>
          <ArrowLeft size={15} />
        </Button>
        <div className="flex items-center gap-2">
          <SeverityBadge severity={alert.severity} />
          <Badge variant="muted">{alert.alert_type.replace(/_/g, " ")}</Badge>
          {alert.is_resolved && <Badge variant="muted">Resolved</Badge>}
        </div>
        <div className="ml-auto flex gap-2">
          {!alert.is_resolved && (
            <Button size="sm" variant="default" onClick={handleResolve} disabled={resolving}>
              {resolving ? <Spinner /> : <><CheckCircle size={13} /> Resolve</>}
            </Button>
          )}
          <Button size="sm" onClick={handleDraft} disabled={drafting || !!alert.draft_response}>
            {drafting ? <Spinner /> : <><Zap size={13} /> Draft response</>}
          </Button>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">{alert.title}</h1>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{alert.description}</p>
          </div>

          {(alert.metric_value != null || alert.metric_baseline != null) && (
            <>
              <Separator />
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">Metrics</p>
                <div className="grid grid-cols-2 gap-4">
                  {alert.metric_value != null && (
                    <div className="border border-border rounded-lg p-4">
                      <p className="text-xs text-muted-foreground">Current value</p>
                      <p className="text-2xl font-semibold tracking-tight mt-1">
                        {typeof alert.metric_value === "number" && alert.metric_value < 1
                          ? `${(alert.metric_value * 100).toFixed(1)}%`
                          : alert.metric_value.toFixed(2)}
                      </p>
                    </div>
                  )}
                  {alert.metric_baseline != null && (
                    <div className="border border-border rounded-lg p-4">
                      <p className="text-xs text-muted-foreground">Baseline</p>
                      <p className="text-2xl font-semibold tracking-tight mt-1">
                        {typeof alert.metric_baseline === "number" && alert.metric_baseline < 1
                          ? `${(alert.metric_baseline * 100).toFixed(1)}%`
                          : alert.metric_baseline.toFixed(2)}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          <Separator />

          <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <MetaRow label="Tracker" value={alert.tracker_name ?? "Cross-channel"} />
            <MetaRow label="Triggered" value={new Date(alert.triggered_at).toLocaleString()} />
            {alert.resolved_at && (
              <MetaRow label="Resolved" value={new Date(alert.resolved_at).toLocaleString()} />
            )}
            <MetaRow label="Agent notified" value={alert.agent_notified ? "Yes" : "No"} />
          </div>
        </div>

        {/* AI Draft Response Panel */}
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">AI Draft Response</p>
          <div className="border border-border rounded-lg p-4">
            {alert.draft_response ? (
              <div>
                <p className="text-xs text-muted-foreground mb-2">Generated by your configured agent</p>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{alert.draft_response}</p>
              </div>
            ) : (
              <div className="text-center py-8 space-y-3">
                <p className="text-sm text-muted-foreground">No draft yet</p>
                <p className="text-xs text-muted-foreground">Click &quot;Draft response&quot; to generate an AI-assisted response via your configured agent webhook.</p>
                <Button size="sm" onClick={handleDraft} disabled={drafting}>
                  {drafting ? <Spinner /> : <><Zap size={13} /> Generate draft</>}
                </Button>
              </div>
            )}
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

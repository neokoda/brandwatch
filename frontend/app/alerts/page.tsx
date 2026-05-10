"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { SeverityBadge } from "@/components/shared/severity-badge";
import { alertsApi } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { Alert } from "@/lib/types";
import { CheckCircle } from "lucide-react";

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString();
}

const ALERT_TYPE_LABELS: Record<string, string> = {
  negativity_surge: "Negativity Surge",
  volume_spike: "Volume Spike",
  crisis_risk: "Crisis Risk",
  velocity_spike: "Velocity Spike",
  cross_channel: "Cross-Channel",
};

export default function AlertsPage() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [severity, setSeverity] = useState("");
  const [resolved, setResolved] = useState("false");

  async function load() {
    setLoading(true);
    try {
      const res = await alertsApi.list({
        severity: severity || undefined,
        is_resolved: resolved === "" ? undefined : resolved === "true",
      });
      setAlerts(res);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [severity, resolved]);

  async function handleResolve(id: string, e: React.MouseEvent) {
    e.preventDefault();
    await alertsApi.resolve(id);
    setAlerts((prev) => prev.map((a) => a.id === id ? { ...a, is_resolved: true } : a));
  }

  return (
    <AppShell accountName={user?.account_name}>
      <PageHeader
        title="Alerts"
        description={`${alerts.filter((a) => !a.is_resolved).length} active`}
      />

      <div className="mt-6 flex gap-3 flex-wrap">
        <Select value={severity} onChange={(e) => setSeverity(e.target.value)} className="w-40">
          <option value="">All severities</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </Select>
        <Select value={resolved} onChange={(e) => setResolved(e.target.value)} className="w-36">
          <option value="false">Active only</option>
          <option value="true">Resolved only</option>
          <option value="">All</option>
        </Select>
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center gap-3 py-16 justify-center">
            <Spinner /> <span className="text-sm text-muted-foreground">Loading...</span>
          </div>
        ) : alerts.length === 0 ? (
          <div className="border border-border rounded-lg">
            <EmptyState title="No alerts" description="Alerts fire automatically when anomalies are detected." />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Severity</TableHead>
                <TableHead>Alert</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Tracker</TableHead>
                <TableHead>Triggered</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.map((a) => (
                <TableRow key={a.id}>
                  <TableCell><SeverityBadge severity={a.severity} /></TableCell>
                  <TableCell>
                    <Link href={`/alerts/${a.id}`} className="font-medium hover:underline">
                      {a.title}
                    </Link>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{a.description}</p>
                  </TableCell>
                  <TableCell>
                    <Badge variant="muted">{ALERT_TYPE_LABELS[a.alert_type] ?? a.alert_type}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">
                    {a.tracker_name ?? "Cross-channel"}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                    {fmtTime(a.triggered_at)}
                  </TableCell>
                  <TableCell>
                    {a.is_resolved ? (
                      <Badge variant="muted">Resolved</Badge>
                    ) : (
                      <Badge variant="negative">Active</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {!a.is_resolved && (
                      <Button size="icon-sm" variant="ghost" onClick={(e) => handleResolve(a.id, e)} title="Mark resolved">
                        <CheckCircle size={14} />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </AppShell>
  );
}

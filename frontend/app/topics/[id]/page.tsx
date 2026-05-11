"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { SentimentBadge } from "@/components/shared/sentiment-badge";
import { SourceBadge } from "@/components/shared/source-badge";
import { topicsApi } from "@/lib/api";
import { useAuth } from "@/components/providers/auth-provider";
import type { Mention } from "@/lib/types";
import { ArrowLeft } from "lucide-react";

export default function TopicDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    topicsApi.mentions(id).then(setMentions).finally(() => setLoading(false));
  }, [id]);

  return (
    <AppShell accountName={user?.account_name}>
      <div className="pb-6 border-b border-border flex items-center gap-3">
        <Button size="icon-sm" variant="ghost" onClick={() => router.back()}>
          <ArrowLeft size={15} />
        </Button>
        <h1 className="text-xl font-semibold tracking-tight">Topic mentions</h1>
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center gap-3 py-16 justify-center">
            <Spinner /> <span className="text-sm text-muted-foreground">Loading...</span>
          </div>
        ) : mentions.length === 0 ? (
          <div className="border border-border rounded-lg">
            <EmptyState title="No mentions in this topic" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Source</TableHead>
                <TableHead>Content</TableHead>
                <TableHead>Sentiment</TableHead>
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
                  </TableCell>
                  <TableCell><SentimentBadge label={m.sentiment_label} /></TableCell>
                  <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                    {new Date(m.ingested_at).toLocaleDateString()}
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

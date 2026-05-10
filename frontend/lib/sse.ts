"use client";

import { useEffect, useRef, useCallback } from "react";
import { getToken } from "./auth";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export interface SSEMention {
  id: string;
  source_channel: string;
  content_excerpt?: string;
  sentiment_label: string;
  ingested_at: string;
}

export function useMentionStream(
  onMention: (m: SSEMention) => void,
  trackerId?: string
) {
  const esRef = useRef<EventSource | null>(null);
  const onMentionRef = useRef(onMention);
  onMentionRef.current = onMention;

  const connect = useCallback(() => {
    const token = getToken();
    if (!token) return;

    const url = `${BASE}/mentions/stream?token=${encodeURIComponent(token)}${trackerId ? `&tracker_id=${trackerId}` : ""}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as SSEMention;
        onMentionRef.current(data);
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
      // Reconnect after 15s
      setTimeout(connect, 15_000);
    };
  }, [trackerId]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
    };
  }, [connect]);
}

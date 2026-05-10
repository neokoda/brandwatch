"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import type { TrendPoint } from "@/lib/types";

function fmtBucket(iso: string, granularity: "hour" | "day" | "week") {
  const d = new Date(iso);
  if (granularity === "hour") {
    return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", hour12: true });
  }
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

interface Props {
  data: TrendPoint[];
  height?: number;
  granularity?: "hour" | "day" | "week";
}

export function TrendChart({ data, height = 280, granularity = "day" }: Props) {
  const formatted = data.map((d) => ({
    ...d,
    label: fmtBucket(d.bucket, granularity),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={formatted} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          interval="preserveStartEnd"
        />
        <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
        <Tooltip
          contentStyle={{
            background: "var(--background)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="total" stroke="var(--foreground)" strokeWidth={1.5} dot={false} name="Total" />
        <Line type="monotone" dataKey="positive" stroke="var(--positive)" strokeWidth={1.5} dot={false} name="Positive" />
        <Line type="monotone" dataKey="negative" stroke="var(--negative)" strokeWidth={1.5} dot={false} name="Negative" />
      </LineChart>
    </ResponsiveContainer>
  );
}

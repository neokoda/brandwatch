"use client";

import { Select } from "@/components/ui/select";
import type { Tracker } from "@/lib/types";

interface Props {
  trackers: Tracker[];
  value: string;
  onChange: (id: string) => void;
  includeAll?: boolean;
}

export function TrackerSelector({ trackers, value, onChange, includeAll = true }: Props) {
  return (
    <Select value={value} onChange={(e) => onChange(e.target.value)} className="w-48">
      {includeAll && <option value="">All trackers</option>}
      {trackers.map((t) => (
        <option key={t.id} value={t.id}>{t.name}</option>
      ))}
    </Select>
  );
}

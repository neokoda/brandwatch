import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Stat } from "@/components/ui/stat";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Search, Plus, RefreshCw, Download } from "lucide-react";

export default function DesignPage() {
  return (
    <div className="min-h-screen bg-background px-16 py-12 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold tracking-tight mb-1">Design System</h1>
      <p className="text-sm text-muted-foreground mb-12">
        Brandwatch — component reference
      </p>

      {/* ── Color Tokens ── */}
      <Section title="Color tokens">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Swatch color="bg-foreground" label="Foreground" hex="#0a0a0a" />
          <Swatch color="bg-background border border-border" label="Background" hex="#ffffff" />
          <Swatch color="bg-surface border border-border" label="Surface" hex="#fafafa" />
          <Swatch color="bg-muted" label="Muted" hex="#f5f5f5" />
          <Swatch color="bg-border" label="Border" hex="#e5e5e5" />
          <SwatchVar bg="var(--positive)" label="Positive" hex="#166534" />
          <SwatchVar bg="var(--negative)" label="Negative" hex="#991b1b" />
          <SwatchVar bg="var(--warning)" label="Warning" hex="#92400e" />
        </div>
      </Section>

      <Separator className="my-10" />

      {/* ── Typography ── */}
      <Section title="Typography">
        <div className="space-y-3">
          <p className="text-2xl font-semibold tracking-tight">Heading / 24px semibold</p>
          <p className="text-xl font-semibold tracking-tight">Heading / 20px semibold</p>
          <p className="text-base font-semibold">Heading / 16px semibold</p>
          <p className="text-sm font-medium">Label / 14px medium</p>
          <p className="text-sm text-foreground">Body / 14px regular</p>
          <p className="text-sm text-muted-foreground">Body muted / 14px</p>
          <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium">
            Overline / 12px uppercase
          </p>
          <p className="text-xs text-muted-foreground">Caption / 12px</p>
        </div>
      </Section>

      <Separator className="my-10" />

      {/* ── Buttons ── */}
      <Section title="Buttons">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Save changes</Button>
          <Button variant="outline">Cancel</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Delete</Button>
          <Button variant="link">Learn more</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3 mt-4">
          <Button size="sm">Small</Button>
          <Button>Default</Button>
          <Button size="lg">Large</Button>
          <Button size="icon"><Plus size={15} /></Button>
          <Button size="icon-sm" variant="outline"><Search size={13} /></Button>
        </div>
        <div className="flex flex-wrap items-center gap-3 mt-4">
          <Button disabled>Disabled</Button>
          <Button variant="outline" disabled>Disabled outline</Button>
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-4">
          <Button size="sm"><Plus size={13} /> New tracker</Button>
          <Button size="sm" variant="outline"><RefreshCw size={13} /> Refresh</Button>
          <Button size="sm" variant="outline"><Download size={13} /> Export</Button>
        </div>
      </Section>

      <Separator className="my-10" />

      {/* ── Badges ── */}
      <Section title="Badges">
        <div className="flex flex-wrap gap-2">
          <Badge variant="default">Default</Badge>
          <Badge variant="outline">Outline</Badge>
          <Badge variant="muted">Muted</Badge>
          <Badge variant="positive">Positive</Badge>
          <Badge variant="negative">Negative</Badge>
          <Badge variant="neutral">Neutral</Badge>
          <Badge variant="warning">Warning</Badge>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          <Badge variant="positive">82% positive</Badge>
          <Badge variant="negative">Crisis risk</Badge>
          <Badge variant="warning">Reviewing</Badge>
          <Badge variant="muted">GDELT</Badge>
          <Badge variant="muted">YouTube</Badge>
          <Badge variant="outline">en</Badge>
        </div>
      </Section>

      <Separator className="my-10" />

      {/* ── Form elements ── */}
      <Section title="Form elements">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Search
            </label>
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input className="pl-8" placeholder="Search mentions..." />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Source
            </label>
            <Select>
              <option value="">All sources</option>
              <option value="gdelt">GDELT</option>
              <option value="youtube">YouTube</option>
              <option value="reddit">Reddit</option>
              <option value="rss">RSS</option>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Sentiment
            </label>
            <Select>
              <option>All sentiments</option>
              <option>Positive</option>
              <option>Negative</option>
              <option>Neutral</option>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Disabled
            </label>
            <Input disabled placeholder="Not available" />
          </div>
        </div>
      </Section>

      <Separator className="my-10" />

      {/* ── Stats ── */}
      <Section title="Stats">
        <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-border">
          <Stat label="Total mentions" value="12,480" delta="8.2% vs last week" deltaPositive />
          <Stat label="Negative share" value="18%" delta="3.1% vs last week" deltaPositive={false} className="pl-6" />
          <Stat label="Avg engagement" value="2.4" delta="0.3 vs last week" deltaPositive className="pl-6" />
          <Stat label="Active alerts" value="3" className="pl-6" />
        </div>
      </Section>

      <Separator className="my-10" />

      {/* ── Table ── */}
      <Section title="Table">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Source</TableHead>
              <TableHead>Content</TableHead>
              <TableHead>Sentiment</TableHead>
              <TableHead>Engagement</TableHead>
              <TableHead>Time</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {[
              { source: "GDELT", content: "McDonald's faces backlash over pricing strategy...", sentiment: "negative", engagement: "4.2K", time: "2m ago" },
              { source: "YouTube", content: "I love the new BigMac, honestly the best burger...", sentiment: "positive", engagement: "1.1K", time: "14m ago" },
              { source: "Reddit", content: "Anyone else notice the quality has dropped lately?", sentiment: "negative", engagement: "892", time: "31m ago" },
              { source: "RSS", content: "McDonald's reports record quarterly earnings...", sentiment: "positive", engagement: "3.7K", time: "1h ago" },
              { source: "Reddit", content: "Their app is okay but nothing special tbh.", sentiment: "neutral", engagement: "143", time: "2h ago" },
            ].map((row, i) => (
              <TableRow key={i}>
                <TableCell>
                  <Badge variant="muted">{row.source}</Badge>
                </TableCell>
                <TableCell className="max-w-xs text-muted-foreground truncate">{row.content}</TableCell>
                <TableCell>
                  <Badge
                    variant={
                      row.sentiment === "positive"
                        ? "positive"
                        : row.sentiment === "negative"
                        ? "negative"
                        : "neutral"
                    }
                  >
                    {row.sentiment}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{row.engagement}</TableCell>
                <TableCell className="text-muted-foreground">{row.time}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Section>

      <Separator className="my-10" />

      {/* ── States ── */}
      <Section title="States">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="border border-border rounded-lg">
            <EmptyState
              title="No mentions yet"
              description="Mentions from GDELT, YouTube, and Reddit will appear here once ingestion starts."
              action={<Button size="sm" variant="outline"><RefreshCw size={13} /> Trigger ingestion</Button>}
            />
          </div>
          <div className="border border-border rounded-lg flex items-center justify-center py-16 gap-3">
            <Spinner />
            <span className="text-sm text-muted-foreground">Loading mentions...</span>
          </div>
        </div>
      </Section>

      <Separator className="my-10" />

      {/* ── Sidebar preview ── */}
      <Section title="Navigation pattern">
        <div className="border border-border rounded-lg overflow-hidden flex h-80">
          {/* Simulated sidebar */}
          <div className="w-56 shrink-0 border-r border-border bg-background flex flex-col">
            <div className="h-14 flex items-center px-5 border-b border-border">
              <span className="text-sm font-semibold tracking-tight">Brandwatch</span>
            </div>
            <div className="px-3 py-3 border-b border-border">
              <div className="flex items-center gap-2 px-2 py-1.5 rounded text-sm font-medium hover:bg-surface transition-colors">
                <span className="flex-1 truncate">McDonald&apos;s</span>
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="text-muted-foreground"><path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </div>
            </div>
            <div className="flex-1 py-2 px-2 space-y-0.5">
              {[
                ["Dashboard", true],
                ["Mentions", false],
                ["Analytics", false],
                ["Alerts", false],
                ["Triage", false],
              ].map(([label, active]) => (
                <div
                  key={label as string}
                  className={`px-2.5 py-2 rounded text-sm ${
                    active
                      ? "bg-foreground text-background font-medium"
                      : "text-muted-foreground"
                  }`}
                >
                  {label as string}
                </div>
              ))}
            </div>
          </div>
          {/* Simulated content */}
          <div className="flex-1 p-6 overflow-hidden">
            <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-4">Dashboard</p>
            <div className="grid grid-cols-3 gap-3 mb-4">
              {["12.4K mentions", "18% negative", "3 alerts"].map((t) => (
                <div key={t} className="border border-border rounded p-3">
                  <p className="text-xs text-muted-foreground">{t.split(" ").slice(1).join(" ")}</p>
                  <p className="text-base font-semibold">{t.split(" ")[0]}</p>
                </div>
              ))}
            </div>
            <div className="border border-border rounded h-24 flex items-center justify-center">
              <span className="text-xs text-muted-foreground">Trend chart</span>
            </div>
          </div>
        </div>
      </Section>

      <div className="mt-16 pb-8 border-t border-border pt-6">
        <p className="text-xs text-muted-foreground">
          Plus Jakarta Sans · #0a0a0a / #ffffff · 6px radius · No gradients
        </p>
      </div>
    </div>
  );
}

/* ─── Helpers ── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-2">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">{title}</p>
      {children}
    </section>
  );
}

function Swatch({ color, label, hex }: { color: string; label: string; hex: string }) {
  return (
    <div>
      <div className={`h-10 rounded ${color}`} />
      <p className="mt-1.5 text-xs font-medium">{label}</p>
      <p className="text-xs text-muted-foreground font-mono">{hex}</p>
    </div>
  );
}

function SwatchVar({ bg, label, hex }: { bg: string; label: string; hex: string }) {
  return (
    <div>
      <div className="h-10 rounded" style={{ background: bg }} />
      <p className="mt-1.5 text-xs font-medium">{label}</p>
      <p className="text-xs text-muted-foreground font-mono">{hex}</p>
    </div>
  );
}

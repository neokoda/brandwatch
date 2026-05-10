export type SentimentLabel = "positive" | "negative" | "neutral" | "unclassified";
export type TriageStatus = "new" | "in_review" | "resolved" | "dismissed";
export type AlertSeverity = "info" | "warning" | "critical";
export type SourceChannel = "gdelt" | "youtube" | "reddit" | "rss" | "hackernews" | "bluesky" | "mastodon" | "playstore" | "appstore";

export interface AuthUser {
  user_id: string;
  email: string;
  role: string;
  account_id: string;
  account_name: string;
  account_slug: string;
}

export interface Tracker {
  id: string;
  account_id: string;
  name: string;
  tracker_type: string;
  keywords: string[];
  languages: string[];
  regions: string[];
  rss_feeds: string[];
  sources: string[];
  is_active: boolean;
  created_at: string;
}

export interface Mention {
  id: string;
  tracker_id: string;
  tracker_name?: string;
  source_channel: SourceChannel;
  source_url: string;
  source_domain?: string;
  author_name?: string;
  is_influencer: boolean;
  region_code?: string;
  language_code?: string;
  content_text: string;
  content_excerpt?: string;
  published_at?: string;
  ingested_at: string;
  engagement_score: number;
  engagement_raw: Record<string, unknown>;
  sentiment_label: SentimentLabel;
  sentiment_score: number;
  emotion_label?: string;
  topic_cluster_id?: string;
  topic_label?: string;
  triage_status: TriageStatus;
  triage_priority?: string;
  triage_assignee?: string;
  triage_note?: string;
  keywords_matched: string[];
}

export interface MentionListResponse {
  items: Mention[];
  total: number;
  page: number;
  page_size: number;
}

export interface Alert {
  id: string;
  account_id: string;
  tracker_id?: string;
  tracker_name?: string;
  alert_type: string;
  severity: AlertSeverity;
  title: string;
  description: string;
  metric_value?: number;
  metric_baseline?: number;
  triggered_at: string;
  is_resolved: boolean;
  resolved_at?: string;
  agent_notified: boolean;
  draft_response?: string;
}

export interface KPIs {
  total_mentions: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  positive_share: number;
  negative_share: number;
  avg_engagement: number;
  active_alerts: number;
  mentions_delta_pct?: number;
  negative_delta_pct?: number;
}

export interface TrendPoint {
  bucket: string;
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  avg_sentiment: number;
  avg_engagement: number;
}

export interface TopicCluster {
  id: string;
  tracker_id: string;
  label: string;
  keywords: string[];
  mention_count: number;
  sentiment_avg: number;
  period_start: string;
  period_end: string;
}

export interface CrossChannelInsight {
  id: string;
  account_id: string;
  insight_text: string;
  related_tracker_ids: string[];
  related_alert_ids: string[];
  generated_at: string;
}

export interface SourceBreakdown {
  source_channel: string;
  mention_count: number;
  positive_count: number;
  negative_count: number;
  avg_engagement: number;
}

export interface GeoPoint {
  region_code: string;
  mention_count: number;
  negative_share: number;
  avg_sentiment: number;
}

export interface LanguageBreakdown {
  language_code: string;
  mention_count: number;
  positive_share: number;
  negative_share: number;
}

export interface EmotionStat {
  emotion_label: string;
  count: number;
  share: number;
}

export interface AuthorStat {
  author_name: string;
  mention_count: number;
  avg_sentiment: number;
  is_influencer: boolean;
  total_engagement: number;
  top_channel: string;
}

export interface VelocityData {
  current_rate: number;
  last_24h_mentions: number;
  baseline_rate: number;
  mentions_per_day: number;
  velocity_ratio: number;
  trend: "up" | "down" | "stable";
  current_negative_share: number;
  baseline_negative_share: number;
  negativity_z: number;
}

export interface Account {
  id: string;
  name: string;
  slug: string;
  agent_webhook_url?: string;
  telegram_chat_id?: string;
  alert_config: Record<string, unknown>;
  created_at: string;
}

export interface IngestionRun {
  id: string;
  tracker_id: string;
  source: string;
  status: string;
  mentions_found: number;
  mentions_stored: number;
  started_at: string;
  finished_at?: string;
  error_message?: string;
}

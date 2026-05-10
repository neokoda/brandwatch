"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("agent_webhook_url", sa.String(500)),
        sa.Column("agent_api_token", sa.String(500)),
        sa.Column("telegram_chat_id", sa.String(100)),
        sa.Column("alert_config", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "trackers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tracker_type", sa.String(50), server_default="brand"),
        sa.Column("keywords", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("languages", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("regions", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("rss_feeds", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "topic_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tracker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("label_raw", sa.String(500)),
        sa.Column("keywords", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("mention_count", sa.Integer, server_default="0"),
        sa.Column("sentiment_avg", sa.Float, server_default="0"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tracker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_channel", sa.String(20), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("source_url_hash", sa.String(64), nullable=False),
        sa.Column("source_domain", sa.String(255)),
        sa.Column("author_name", sa.String(255)),
        sa.Column("author_id", sa.String(255)),
        sa.Column("author_follower_count", sa.Integer, server_default="0"),
        sa.Column("is_influencer", sa.Boolean, server_default="false"),
        sa.Column("region_code", sa.String(10)),
        sa.Column("language_code", sa.String(10)),
        sa.Column("content_text", sa.Text, nullable=False),
        sa.Column("content_excerpt", sa.String(500)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("engagement_score", sa.Float, server_default="0"),
        sa.Column("engagement_raw", postgresql.JSONB, server_default="{}"),
        sa.Column("sentiment_label", sa.String(20), server_default="unclassified"),
        sa.Column("sentiment_score", sa.Float, server_default="0"),
        sa.Column("sentiment_scores", postgresql.JSONB, server_default="{}"),
        sa.Column("emotion_label", sa.String(50)),
        sa.Column("emotion_score", sa.Float),
        sa.Column("topic_cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topic_clusters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("keywords_matched", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("triage_status", sa.String(20), server_default="new"),
        sa.Column("triage_priority", sa.String(20)),
        sa.Column("triage_assignee", sa.String(255)),
        sa.Column("triage_note", sa.Text),
        sa.Column("triage_updated_at", sa.DateTime(timezone=True)),
        sa.Column("is_alert_triggered", sa.Boolean, server_default="false"),
        sa.Column("raw_payload", postgresql.JSONB, server_default="{}"),
    )

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tracker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trackers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("metric_value", sa.Float),
        sa.Column("metric_baseline", sa.Float),
        sa.Column("threshold_used", sa.Float),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_resolved", sa.Boolean, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("agent_notified", sa.Boolean, server_default="false"),
        sa.Column("draft_response", sa.Text),
    )

    op.create_table(
        "cross_channel_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("insight_text", sa.Text, nullable=False),
        sa.Column("related_tracker_ids", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("related_alert_ids", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sentiment_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tracker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_channel", sa.String(20)),
        sa.Column("region_code", sa.String(10)),
        sa.Column("language_code", sa.String(10)),
        sa.Column("hour_bucket", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mention_count", sa.Integer, server_default="0"),
        sa.Column("positive_count", sa.Integer, server_default="0"),
        sa.Column("negative_count", sa.Integer, server_default="0"),
        sa.Column("neutral_count", sa.Integer, server_default="0"),
        sa.Column("avg_sentiment_score", sa.Float, server_default="0"),
        sa.Column("avg_engagement", sa.Float, server_default="0"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tracker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="running"),
        sa.Column("mentions_found", sa.Integer, server_default="0"),
        sa.Column("mentions_stored", sa.Integer, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
    )

    op.create_table(
        "saved_filters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tracker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trackers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("filter_params", postgresql.JSONB, server_default="{}"),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes for common query patterns
    op.create_index("ix_mentions_tracker_id", "mentions", ["tracker_id"])
    op.create_index("ix_mentions_ingested_at", "mentions", ["ingested_at"])
    op.create_index("ix_mentions_sentiment_label", "mentions", ["sentiment_label"])
    op.create_index("ix_mentions_triage_status", "mentions", ["triage_status"])
    op.create_index("ix_mentions_source_url_hash_tracker", "mentions", ["source_url_hash", "tracker_id"])
    op.create_index("ix_snapshots_tracker_hour", "sentiment_snapshots", ["tracker_id", "hour_bucket"])
    op.create_index("ix_alerts_account_id", "alerts", ["account_id"])
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"])


def downgrade() -> None:
    op.drop_table("saved_filters")
    op.drop_table("ingestion_runs")
    op.drop_table("sentiment_snapshots")
    op.drop_table("cross_channel_insights")
    op.drop_table("alerts")
    op.drop_table("mentions")
    op.drop_table("topic_clusters")
    op.drop_table("trackers")
    op.drop_table("users")
    op.drop_table("accounts")

"""add dominant_sentiment to topic_clusters

Revision ID: 003
Revises: 002
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("topic_clusters", sa.Column("dominant_sentiment", sa.String(20), nullable=True))


def downgrade():
    op.drop_column("topic_clusters", "dominant_sentiment")

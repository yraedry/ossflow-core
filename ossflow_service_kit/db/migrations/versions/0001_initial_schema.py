"""initial unified schema

Revision ID: 0001
Revises:
Create Date: 2026-04-15

"""
from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "library_items",
        sa.Column("path", sa.String(), primary_key=True),
        sa.Column("title", sa.String()),
        sa.Column("poster_path", sa.String()),
        sa.Column("size_bytes", sa.BigInteger()),
        sa.Column("duration_s", sa.Float()),
        sa.Column("scanned_at", sa.DateTime()),
        sa.Column("season_dir", sa.String(), index=True),
    )
    op.create_table(
        "library_chapters",
        sa.Column("chapter_path", sa.String(), primary_key=True),
        sa.Column(
            "parent_path",
            sa.String(),
            sa.ForeignKey("library_items.path", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("index_num", sa.Integer()),
        sa.Column("title", sa.String()),
    )
    op.create_table(
        "media_metadata",
        sa.Column("video_path", sa.String(), primary_key=True),
        sa.Column("oracle_data", sa.Text()),
        sa.Column("subs_path", sa.String()),
        sa.Column("dub_path", sa.String()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("input_path", sa.String(), nullable=False),
        sa.Column("output_dir", sa.String()),
        sa.Column("options", sa.Text()),
        sa.Column("diff", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("duration_s", sa.Float()),
    )
    op.create_index("idx_pipelines_started", "pipelines", ["started_at"])
    op.create_table(
        "pipeline_steps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "pipeline_id",
            sa.String(),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("duration_s", sa.Float()),
        sa.Column("error", sa.Text()),
    )
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, index=True),
        sa.Column("payload", sa.Text()),
        sa.Column("result", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
    )
    # Note: telegram_fetcher owns its own tables (channels, media,
    # download_jobs, schema_version) in the same physical DB file. Those
    # are created by telegram_fetcher.db on init — not by Alembic here.


def downgrade() -> None:
    op.drop_table("background_jobs")
    op.drop_table("pipeline_steps")
    op.drop_index("idx_pipelines_started", table_name="pipelines")
    op.drop_table("pipelines")
    op.drop_table("media_metadata")
    op.drop_table("library_chapters")
    op.drop_table("library_items")
    op.drop_table("settings")

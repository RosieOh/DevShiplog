"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-31

users / style_profiles / sources / drafts / draft_versions / risk_findings
/ jobs / usage_logs 8개 테이블을 생성한다.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "style_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("blog_url", sa.String(500), nullable=False),
        sa.Column("sample_count", sa.Integer(), server_default="5"),
        sa.Column(
            "status",
            sa.Enum("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", name="styleprofilestatus"),
            server_default="QUEUED",
        ),
        sa.Column("profile_json", sa.JSON(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_style_profiles_user_id", "style_profiles", ["user_id"])

    op.create_table(
        "sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("type", sa.Enum("URL", "RAW", name="sourcetype"), nullable=False),
        sa.Column("origin", sa.String(500), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_ref", sa.String(500), nullable=True),
        sa.Column("extracted_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sources_user_id", "sources", ["user_id"])

    op.create_table(
        "drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(50), nullable=True),
        sa.Column("audience", sa.String(50), nullable=True),
        sa.Column("length_preset", sa.String(50), nullable=True),
        sa.Column("style_profile_id", sa.String(36), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "ARCHIVED", name="draftstatus"),
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["style_profile_id"], ["style_profiles.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_drafts_user_id", "drafts", ["user_id"])

    op.create_table(
        "draft_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("draft_id", sa.String(36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=True),
        sa.Column("content_ref", sa.String(500), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["draft_id"], ["drafts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("draft_id", "version_no", name="unique_draft_version"),
    )
    op.create_index("ix_draft_versions_draft_id", "draft_versions", ["draft_id"])

    op.create_table(
        "risk_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("draft_version_id", sa.String(36), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "TOKEN", "EMAIL", "PHONE", "INTERNAL_URL", "COMPANY", "SECRET",
                name="riskcategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("LOW", "MED", "HIGH", name="riskseverity"),
            server_default="MED",
        ),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("location_json", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("OPEN", "MASKED", "DELETED", "IGNORED", name="riskstatus"),
            server_default="OPEN",
        ),
        sa.Column("ignore_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["draft_version_id"], ["draft_versions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_risk_findings_draft_version_id", "risk_findings", ["draft_version_id"])
    op.create_index("ix_risk_findings_status", "risk_findings", ["status"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column(
            "type",
            sa.Enum("EXTRACT", "STYLE", "DRAFT", "TRANSFORM", "SAFETY", name="jobtype"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", name="jobstatus"),
            server_default="QUEUED",
        ),
        sa.Column("progress", sa.Integer(), server_default="0"),
        sa.Column("result_ref", sa.JSON(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])

    op.create_table(
        "usage_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_usage_logs_user_id", "usage_logs", ["user_id"])
    op.create_index("ix_usage_logs_created_at", "usage_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("usage_logs")
    op.drop_table("jobs")
    op.drop_table("risk_findings")
    op.drop_table("draft_versions")
    op.drop_table("drafts")
    op.drop_table("sources")
    op.drop_table("style_profiles")
    op.drop_table("users")

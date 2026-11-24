"""agent actions + automation settings

Revision ID: a1b2c3d4e5f6
Revises: 68fbc28bd6b1
Create Date: 2026-11-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "68fbc28bd6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    kind = postgresql.ENUM(
        "due_reminders",
        "daily_summary_sms",
        "low_stock_alert",
        "expiring_alert",
        "reorder_draft",
        name="agent_action_kind",
        create_type=False,
    )
    mode = postgresql.ENUM("auto", "approval", name="agent_action_mode", create_type=False)
    status = postgresql.ENUM(
        "pending",
        "approved",
        "rejected",
        "executed",
        "failed",
        "skipped",
        name="agent_action_status",
        create_type=False,
    )
    kind.create(bind, checkfirst=True)
    mode.create(bind, checkfirst=True)
    status.create(bind, checkfirst=True)

    op.create_table(
        "agent_actions",
        sa.Column("kind", kind, nullable=False),
        sa.Column("mode", mode, nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("decided_by", sa.UUID(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_actions_kind", "agent_actions", ["kind"])
    op.create_index("ix_agent_actions_mode", "agent_actions", ["mode"])
    op.create_index("ix_agent_actions_status", "agent_actions", ["status"])

    op.create_table(
        "automation_settings",
        sa.Column("autopilot_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auto_due_reminders", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("auto_daily_sms", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("auto_low_stock_alerts", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auto_expiring_alerts", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auto_reorder_draft", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_phone", sa.String(length=30), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("automation_settings")
    op.drop_index("ix_agent_actions_status", table_name="agent_actions")
    op.drop_index("ix_agent_actions_mode", table_name="agent_actions")
    op.drop_index("ix_agent_actions_kind", table_name="agent_actions")
    op.drop_table("agent_actions")
    op.execute("DROP TYPE IF EXISTS agent_action_status")
    op.execute("DROP TYPE IF EXISTS agent_action_mode")
    op.execute("DROP TYPE IF EXISTS agent_action_kind")

"""Initial messages table

Revision ID: 001
Revises:
Create Date: 2026-03-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

message_status = postgresql.ENUM(
    "QUEUED", "ACCEPTED", "SENT", "DELIVERED", "FAILED", "CANCELLED",
    name="message_status",
    create_type=False,
)


def upgrade() -> None:
    # Create enum only if it doesn't exist (idempotent for re-runs)
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE message_status AS ENUM (
                'QUEUED', 'ACCEPTED', 'SENT', 'DELIVERED', 'FAILED', 'CANCELLED'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    conn = op.get_bind()
    if not inspect(conn).has_table("messages"):
        op.create_table(
            "messages",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("phone_number", sa.String(20), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
            sa.Column(
                "status",
                message_status,
                nullable=False,
                server_default="QUEUED",
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("gateway_message_id", sa.String(100), nullable=True),
            sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

        op.create_index(
            "ix_messages_queue",
            "messages",
            ["status", "scheduled_at", "created_at"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    if inspect(conn).has_table("messages"):
        op.drop_index("ix_messages_queue", table_name="messages")
        op.drop_table("messages")
    op.execute("DROP TYPE IF EXISTS message_status CASCADE")

"""通知记录保存跳转链接和内容快照

Revision ID: 20260525_0006
Revises: 20260525_0005
Create Date: 2026-05-25 04:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260525_0006"
down_revision = "20260525_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为通知失败重试保留原始跳转链接和摘要内容。"""
    with op.batch_alter_table("notification_deliveries") as batch_op:
        batch_op.add_column(sa.Column("action_url", sa.String(length=512), nullable=True, comment="通知跳转链接"))
        batch_op.add_column(sa.Column("payload_snapshot", sa.JSON(), nullable=True, comment="通知内容快照，用于失败重试"))


def downgrade() -> None:
    """移除通知重试内容快照字段。"""
    with op.batch_alter_table("notification_deliveries") as batch_op:
        batch_op.drop_column("payload_snapshot")
        batch_op.drop_column("action_url")

"""允许失败同步记录没有外部 ID

Revision ID: 20260525_0005
Revises: 20260525_0004
Create Date: 2026-05-25 03:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260525_0005"
down_revision = "20260525_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """外部同步失败时通常拿不到 external_id，因此该字段必须允许为空。"""
    with op.batch_alter_table("external_id_mappings") as batch_op:
        batch_op.alter_column(
            "external_id",
            existing_type=sa.String(length=128),
            nullable=True,
            existing_comment="外部对象 ID",
        )


def downgrade() -> None:
    """回滚为必须有外部 ID。"""
    with op.batch_alter_table("external_id_mappings") as batch_op:
        batch_op.alter_column(
            "external_id",
            existing_type=sa.String(length=128),
            nullable=False,
            existing_comment="外部对象 ID",
        )

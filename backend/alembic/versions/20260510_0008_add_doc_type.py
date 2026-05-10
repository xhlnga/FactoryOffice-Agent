"""add doc_type to documents

Revision ID: 20260510_0008
Revises: 20260510_0007
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260510_0008"
down_revision: Union[str, None] = "20260510_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "doc_type",
            sa.String(32),
            nullable=False,
            server_default="'general'",
            comment="文档结构类型：policy / manual / general",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "doc_type")

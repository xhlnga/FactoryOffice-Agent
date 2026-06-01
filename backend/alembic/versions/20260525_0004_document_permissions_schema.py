"""新增知识库文档权限表

Revision ID: 20260525_0004
Revises: 20260525_0003
Create Date: 2026-05-25 02:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260525_0004"
down_revision = "20260525_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建文档权限表，用于 RAG 检索前的权限过滤。"""
    op.create_table(
        "document_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, comment="文档权限 ID"),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            comment="文档 ID",
        ),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=True, comment="企业 ID"),
        sa.Column("principal_type", sa.String(length=32), nullable=False, comment="授权主体类型"),
        sa.Column("principal_id", sa.String(length=128), nullable=False, comment="授权主体 ID"),
        sa.Column("permission", sa.String(length=32), nullable=False, comment="权限动作"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, comment="授权创建人"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
        sa.UniqueConstraint(
            "document_id",
            "principal_type",
            "principal_id",
            "permission",
            name="uq_document_permissions_scope",
        ),
    )
    op.create_index("ix_document_permissions_document_id", "document_permissions", ["document_id"])
    op.create_index("ix_document_permissions_enterprise_id", "document_permissions", ["enterprise_id"])
    op.create_index("ix_document_permissions_principal_type", "document_permissions", ["principal_type"])
    op.create_index("ix_document_permissions_principal_id", "document_permissions", ["principal_id"])


def downgrade() -> None:
    """回滚文档权限表。"""
    op.drop_index("ix_document_permissions_principal_id", table_name="document_permissions")
    op.drop_index("ix_document_permissions_principal_type", table_name="document_permissions")
    op.drop_index("ix_document_permissions_enterprise_id", table_name="document_permissions")
    op.drop_index("ix_document_permissions_document_id", table_name="document_permissions")
    op.drop_table("document_permissions")

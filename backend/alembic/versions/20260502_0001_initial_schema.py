"""初始化业务表和 pgvector 扩展

Revision ID: 20260502_0001
Revises:
Create Date: 2026-05-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa

from app.models.document_chunk import Vector


revision = "20260502_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建项目基础表结构。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, comment="用户 ID"),
        sa.Column("username", sa.String(length=64), nullable=False, comment="用户名"),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "MANAGER", "EMPLOYEE", name="user_role"),
            nullable=False,
            comment="用户角色",
        ),
        sa.Column("department", sa.String(length=128), nullable=True, comment="所属部门"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, comment="文档 ID"),
        sa.Column("filename", sa.String(length=255), nullable=False, comment="原始文件名"),
        sa.Column("title", sa.String(length=255), nullable=False, comment="文档标题"),
        sa.Column("category", sa.String(length=64), nullable=False, comment="文档分类"),
        sa.Column("file_path", sa.String(length=512), nullable=True, comment="本地文件路径"),
        sa.Column("content_type", sa.String(length=128), nullable=True, comment="文件 MIME 类型"),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True, comment="文件大小，单位字节"),
        sa.Column("file_sha256", sa.String(length=64), nullable=True, comment="文件 SHA-256 摘要"),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, comment="上传人 ID"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_documents_file_sha256", "documents", ["file_sha256"])
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, comment="切块 ID"),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            comment="文档 ID",
        ),
        sa.Column("chunk_text", sa.Text(), nullable=False, comment="切块文本"),
        sa.Column("chunk_index", sa.Integer(), nullable=False, comment="切块序号"),
        sa.Column("embedding", Vector(1536), nullable=True, comment="文档切块向量"),
        sa.Column("chunk_metadata", sa.JSON(), nullable=False, comment="切块元数据"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, comment="任务 ID"),
        sa.Column("title", sa.String(length=255), nullable=False, comment="任务标题"),
        sa.Column("description", sa.Text(), nullable=False, comment="任务描述"),
        sa.Column("assignee", sa.String(length=128), nullable=True, comment="负责人"),
        sa.Column("due_date", sa.Date(), nullable=True, comment="截止日期"),
        sa.Column(
            "priority",
            sa.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="task_priority"),
            nullable=False,
            comment="优先级",
        ),
        sa.Column(
            "status",
            sa.Enum("TODO", "IN_PROGRESS", "DONE", "CANCELLED", name="task_status"),
            nullable=False,
            comment="任务状态",
        ),
        sa.Column("source", sa.String(length=128), nullable=True, comment="任务来源"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True, comment="工单 ID"),
        sa.Column("ticket_type", sa.String(length=64), nullable=False, comment="工单类型"),
        sa.Column("title", sa.String(length=255), nullable=False, comment="工单标题"),
        sa.Column("description", sa.Text(), nullable=False, comment="工单描述"),
        sa.Column(
            "priority",
            sa.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="ticket_priority"),
            nullable=False,
            comment="优先级",
        ),
        sa.Column(
            "status",
            sa.Enum("OPEN", "PROCESSING", "RESOLVED", "CLOSED", name="ticket_status"),
            nullable=False,
            comment="工单状态",
        ),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, comment="创建人 ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )

    op.create_table(
        "purchase_requests",
        sa.Column("id", sa.Integer(), primary_key=True, comment="采购申请 ID"),
        sa.Column("item_name", sa.String(length=255), nullable=False, comment="物品名称"),
        sa.Column("quantity", sa.Integer(), nullable=False, comment="数量"),
        sa.Column("reason", sa.Text(), nullable=False, comment="采购原因"),
        sa.Column("budget", sa.Float(), nullable=True, comment="预算金额"),
        sa.Column("supplier", sa.String(length=255), nullable=True, comment="供应商"),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", name="purchase_status"),
            nullable=False,
            comment="采购状态",
        ),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, comment="创建人 ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )

    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), primary_key=True, comment="审批 ID"),
        sa.Column("action_type", sa.String(length=128), nullable=False, comment="动作类型"),
        sa.Column("action_payload", sa.JSON(), nullable=False, comment="动作参数"),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "EXECUTION_FAILED", name="approval_status"),
            nullable=False,
            comment="审批状态",
        ),
        sa.Column("reviewer", sa.String(length=128), nullable=True, comment="审批人"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True, comment="审批时间"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True, comment="执行时间"),
        sa.Column("execution_result", sa.JSON(), nullable=True, comment="执行结果"),
        sa.Column("comment", sa.String(length=512), nullable=True, comment="审批意见"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, comment="审计日志 ID"),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, comment="用户 ID"),
        sa.Column("action", sa.String(length=128), nullable=False, comment="动作名称"),
        sa.Column("input", sa.Text(), nullable=True, comment="用户输入"),
        sa.Column("output", sa.Text(), nullable=True, comment="模型或工具输出"),
        sa.Column("tool_name", sa.String(length=128), nullable=True, comment="工具名称"),
        sa.Column("tool_args", sa.JSON(), nullable=True, comment="工具参数"),
        sa.Column(
            "status",
            sa.Enum("SUCCESS", "FAILED", "PENDING", name="audit_status"),
            nullable=False,
            comment="执行状态",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )


def downgrade() -> None:
    """回滚基础表结构。

    不主动删除 vector 扩展，避免影响同一数据库中的其他业务对象。
    """
    op.drop_table("audit_logs")

    op.drop_table("approvals")

    op.drop_table("purchase_requests")

    op.drop_table("tickets")

    op.drop_table("tasks")

    op.drop_table("document_chunks")

    op.drop_index("ix_documents_deleted_at", table_name="documents")
    op.drop_index("ix_documents_file_sha256", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    for enum_name in [
        "audit_status",
        "approval_status",
        "purchase_status",
        "ticket_status",
        "ticket_priority",
        "task_status",
        "task_priority",
        "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

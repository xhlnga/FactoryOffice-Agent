"""新增多级审批引擎表

Revision ID: 20260525_0003
Revises: 20260525_0002
Create Date: 2026-05-25 01:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260525_0003"
down_revision = "20260525_0002"
branch_labels = None
depends_on = None


approval_template_status = postgresql.ENUM(
    "ENABLED",
    "DISABLED",
    name="approval_template_status",
    create_type=False,
)
approval_step_mode = postgresql.ENUM("ANY", "ALL", name="approval_step_mode", create_type=False)
approver_type = postgresql.ENUM(
    "USER",
    "ROLE",
    "DEPARTMENT_MANAGER",
    "EXPRESSION",
    name="approver_type",
    create_type=False,
)
approval_instance_status = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "WITHDRAWN",
    "TRANSFERRED",
    "ESCALATED",
    name="approval_instance_status",
    create_type=False,
)
approval_step_status = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "TRANSFERRED",
    "SKIPPED",
    "ESCALATED",
    name="approval_step_status",
    create_type=False,
)
approval_action_type = postgresql.ENUM(
    "APPROVE",
    "REJECT",
    "TRANSFER",
    "WITHDRAW",
    "COMMENT",
    "ESCALATE",
    name="approval_action_type",
    create_type=False,
)


def upgrade() -> None:
    """创建审批模板、审批实例、审批步骤和审批动作表。"""
    bind = op.get_bind()
    for enum_type in [
        approval_template_status,
        approval_step_mode,
        approver_type,
        approval_instance_status,
        approval_step_status,
        approval_action_type,
    ]:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "approval_templates",
        sa.Column("id", sa.Integer(), primary_key=True, comment="审批模板 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=True, comment="企业 ID"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="模板名称"),
        sa.Column("business_type", sa.String(length=128), nullable=False, comment="业务类型或动作类型"),
        sa.Column("description", sa.Text(), nullable=True, comment="模板说明"),
        sa.Column("min_amount", sa.Float(), nullable=True, comment="适用最小金额，含边界"),
        sa.Column("max_amount", sa.Float(), nullable=True, comment="适用最大金额，不含边界"),
        sa.Column("status", approval_template_status, nullable=False, comment="模板状态"),
        sa.Column("is_default", sa.Boolean(), nullable=False, comment="是否默认模板"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_approval_templates_enterprise_id", "approval_templates", ["enterprise_id"])
    op.create_index(
        "ix_approval_templates_business_enabled",
        "approval_templates",
        ["business_type", "status"],
    )

    op.create_table(
        "approval_steps",
        sa.Column("id", sa.Integer(), primary_key=True, comment="审批步骤 ID"),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("approval_templates.id", ondelete="CASCADE"),
            nullable=False,
            comment="审批模板 ID",
        ),
        sa.Column("step_order", sa.Integer(), nullable=False, comment="步骤顺序"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="步骤名称"),
        sa.Column("approver_type", approver_type, nullable=False, comment="审批人选择方式"),
        sa.Column("approver_value", sa.String(length=128), nullable=False, comment="审批人、角色或表达式"),
        sa.Column("mode", approval_step_mode, nullable=False, comment="会签/或签模式"),
        sa.Column("timeout_hours", sa.Integer(), nullable=True, comment="超时小时数"),
        sa.Column("escalate_to", sa.String(length=128), nullable=True, comment="超时升级到角色或人员"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_approval_steps_template_id", "approval_steps", ["template_id"])

    op.create_table(
        "approval_instances",
        sa.Column("id", sa.Integer(), primary_key=True, comment="审批实例 ID"),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("approval_templates.id"), nullable=True, comment="审批模板 ID"),
        sa.Column("approval_id", sa.Integer(), sa.ForeignKey("approvals.id"), nullable=True, comment="兼容审批 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=True, comment="企业 ID"),
        sa.Column("business_type", sa.String(length=128), nullable=False, comment="业务类型"),
        sa.Column("business_id", sa.String(length=64), nullable=True, comment="业务对象 ID"),
        sa.Column("title", sa.String(length=255), nullable=False, comment="审批标题"),
        sa.Column("status", approval_instance_status, nullable=False, comment="审批实例状态"),
        sa.Column("current_step_order", sa.Integer(), nullable=True, comment="当前步骤顺序"),
        sa.Column("created_by", sa.String(length=128), nullable=True, comment="发起人"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True, comment="完成时间"),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True, comment="撤回时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_approval_instances_template_id", "approval_instances", ["template_id"])
    op.create_index("ix_approval_instances_approval_id", "approval_instances", ["approval_id"])
    op.create_index("ix_approval_instances_enterprise_id", "approval_instances", ["enterprise_id"])

    op.create_table(
        "approval_instance_steps",
        sa.Column("id", sa.Integer(), primary_key=True, comment="审批实例步骤 ID"),
        sa.Column(
            "instance_id",
            sa.Integer(),
            sa.ForeignKey("approval_instances.id", ondelete="CASCADE"),
            nullable=False,
            comment="审批实例 ID",
        ),
        sa.Column("template_step_id", sa.Integer(), sa.ForeignKey("approval_steps.id"), nullable=True, comment="模板步骤 ID"),
        sa.Column("step_order", sa.Integer(), nullable=False, comment="步骤顺序"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="步骤名称"),
        sa.Column("approver_type", approver_type, nullable=False, comment="审批人选择方式"),
        sa.Column("approver_value", sa.String(length=128), nullable=False, comment="审批人、角色或表达式"),
        sa.Column("assigned_to", sa.String(length=128), nullable=True, comment="当前处理人或角色"),
        sa.Column("mode", approval_step_mode, nullable=False, comment="会签/或签模式"),
        sa.Column("status", approval_step_status, nullable=False, comment="步骤状态"),
        sa.Column("timeout_hours", sa.Integer(), nullable=True, comment="超时小时数"),
        sa.Column("escalate_to", sa.String(length=128), nullable=True, comment="超时升级到角色或人员"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True, comment="批准时间"),
        sa.Column("comment", sa.String(length=512), nullable=True, comment="审批意见"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_approval_instance_steps_instance_id", "approval_instance_steps", ["instance_id"])

    op.create_table(
        "approval_actions",
        sa.Column("id", sa.Integer(), primary_key=True, comment="审批动作 ID"),
        sa.Column(
            "instance_id",
            sa.Integer(),
            sa.ForeignKey("approval_instances.id", ondelete="CASCADE"),
            nullable=False,
            comment="审批实例 ID",
        ),
        sa.Column("step_id", sa.Integer(), sa.ForeignKey("approval_instance_steps.id"), nullable=True, comment="审批步骤 ID"),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, comment="操作人用户 ID"),
        sa.Column("actor_name", sa.String(length=128), nullable=False, comment="操作人名称"),
        sa.Column("action", approval_action_type, nullable=False, comment="审批动作"),
        sa.Column("comment", sa.String(length=512), nullable=True, comment="操作意见"),
        sa.Column("from_approver", sa.String(length=128), nullable=True, comment="转交前处理人"),
        sa.Column("to_approver", sa.String(length=128), nullable=True, comment="转交后处理人"),
        sa.Column("action_metadata", sa.JSON(), nullable=False, comment="动作元数据"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_approval_actions_instance_id", "approval_actions", ["instance_id"])
    op.create_index("ix_approval_actions_step_id", "approval_actions", ["step_id"])
    op.create_index("ix_approval_actions_actor_user_id", "approval_actions", ["actor_user_id"])


def downgrade() -> None:
    """回滚审批引擎表。"""
    op.drop_index("ix_approval_actions_actor_user_id", table_name="approval_actions")
    op.drop_index("ix_approval_actions_step_id", table_name="approval_actions")
    op.drop_index("ix_approval_actions_instance_id", table_name="approval_actions")
    op.drop_table("approval_actions")

    op.drop_index("ix_approval_instance_steps_instance_id", table_name="approval_instance_steps")
    op.drop_table("approval_instance_steps")

    op.drop_index("ix_approval_instances_enterprise_id", table_name="approval_instances")
    op.drop_index("ix_approval_instances_approval_id", table_name="approval_instances")
    op.drop_index("ix_approval_instances_template_id", table_name="approval_instances")
    op.drop_table("approval_instances")

    op.drop_index("ix_approval_steps_template_id", table_name="approval_steps")
    op.drop_table("approval_steps")

    op.drop_index("ix_approval_templates_business_enabled", table_name="approval_templates")
    op.drop_index("ix_approval_templates_enterprise_id", table_name="approval_templates")
    op.drop_table("approval_templates")

    bind = op.get_bind()
    for enum_type in [
        approval_action_type,
        approval_step_status,
        approval_instance_status,
        approver_type,
        approval_step_mode,
        approval_template_status,
    ]:
        enum_type.drop(bind, checkfirst=True)

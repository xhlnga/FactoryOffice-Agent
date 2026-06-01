"""新增企业集成、组织、幂等、通知和 SLA 表

Revision ID: 20260525_0002
Revises: 20260502_0001
Create Date: 2026-05-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260525_0002"
down_revision = "20260502_0001"
branch_labels = None
depends_on = None


user_status = sa.Enum("ACTIVE", "DISABLED", "LEFT", "LOCKED", name="user_status")


def upgrade() -> None:
    """创建企业集成基础表，并兼容增强 users。"""
    bind = op.get_bind()
    # add_column 不会像 create_table 那样可靠地自动创建 PostgreSQL enum 类型。
    user_status.create(bind, checkfirst=True)

    op.create_table(
        "enterprises",
        sa.Column("id", sa.Integer(), primary_key=True, comment="企业 ID"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="企业名称"),
        sa.Column("code", sa.String(length=64), nullable=False, comment="企业编码"),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "DISABLED", name="enterprise_status"),
            nullable=False,
            comment="企业状态",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_enterprises_name", "enterprises", ["name"], unique=True)
    op.create_index("ix_enterprises_code", "enterprises", ["code"], unique=True)

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True, comment="部门 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=False, comment="企业 ID"),
        sa.Column("external_department_id", sa.String(length=128), nullable=True, comment="外部平台部门 ID"),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True, comment="上级部门 ID"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="部门名称"),
        sa.Column("path", sa.String(length=512), nullable=True, comment="部门路径"),
        sa.Column("sort_order", sa.Integer(), nullable=False, comment="排序值"),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "DISABLED", name="department_status"),
            nullable=False,
            comment="部门状态",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
        sa.UniqueConstraint("enterprise_id", "external_department_id", name="uq_departments_enterprise_external"),
    )
    op.create_index("ix_departments_enterprise_id", "departments", ["enterprise_id"])
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"])

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, comment="角色 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=False, comment="企业 ID"),
        sa.Column("code", sa.String(length=64), nullable=False, comment="角色编码"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="角色名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="角色说明"),
        sa.Column("is_system", sa.Boolean(), nullable=False, comment="是否系统内置角色"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
        sa.UniqueConstraint("enterprise_id", "code", name="uq_roles_enterprise_code"),
    )
    op.create_index("ix_roles_enterprise_id", "roles", ["enterprise_id"])

    op.add_column("users", sa.Column("enterprise_id", sa.Integer(), nullable=True, comment="所属企业 ID"))
    op.add_column("users", sa.Column("external_user_id", sa.String(length=128), nullable=True, comment="外部平台用户 ID"))
    op.add_column("users", sa.Column("department_id", sa.Integer(), nullable=True, comment="部门 ID"))
    op.add_column("users", sa.Column("position", sa.String(length=128), nullable=True, comment="岗位"))
    op.add_column("users", sa.Column("mobile_hash", sa.String(length=128), nullable=True, comment="手机号哈希"))
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True, comment="邮箱"))
    op.add_column(
        "users",
        sa.Column(
            "status",
            user_status,
            nullable=False,
            server_default="ACTIVE",
            comment="账号状态",
        ),
    )
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否系统管理员"),
    )
    op.create_foreign_key("fk_users_enterprise_id_enterprises", "users", "enterprises", ["enterprise_id"], ["id"])
    op.create_foreign_key("fk_users_department_id_departments", "users", "departments", ["department_id"], ["id"])
    op.create_index("ix_users_enterprise_id", "users", ["enterprise_id"])
    op.create_index("ix_users_external_user_id", "users", ["external_user_id"])
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("uq_users_enterprise_external_user", "users", ["enterprise_id", "external_user_id"], unique=True)

    op.create_table(
        "integration_configs",
        sa.Column("id", sa.Integer(), primary_key=True, comment="集成配置 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=False, comment="企业 ID"),
        sa.Column("platform", sa.String(length=64), nullable=False, comment="平台类型"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="配置名称"),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "DISABLED", name="integration_config_status"),
            nullable=False,
            comment="配置状态",
        ),
        sa.Column("corp_id", sa.String(length=128), nullable=True, comment="企业 ID 或 CorpId"),
        sa.Column("app_key", sa.String(length=128), nullable=True, comment="应用 Key"),
        sa.Column("agent_id", sa.String(length=128), nullable=True, comment="应用 AgentId"),
        sa.Column("encrypted_config", sa.JSON(), nullable=False, comment="加密配置或密钥引用"),
        sa.Column("webhook_url", sa.String(length=512), nullable=True, comment="Webhook 地址"),
        sa.Column("callback_url", sa.String(length=512), nullable=True, comment="回调地址"),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True, comment="最后健康检查时间"),
        sa.Column("last_health_status", sa.String(length=64), nullable=True, comment="最后健康检查状态"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
        sa.UniqueConstraint(
            "enterprise_id",
            "platform",
            "name",
            name="uq_integration_configs_enterprise_platform_name",
        ),
    )
    op.create_index("ix_integration_configs_enterprise_id", "integration_configs", ["enterprise_id"])

    op.create_table(
        "external_id_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, comment="映射 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=True, comment="企业 ID"),
        sa.Column("object_type", sa.String(length=64), nullable=False, comment="本地对象类型"),
        sa.Column("local_id", sa.String(length=64), nullable=False, comment="本地对象 ID"),
        sa.Column("external_system", sa.String(length=64), nullable=False, comment="外部系统"),
        sa.Column("external_id", sa.String(length=128), nullable=False, comment="外部对象 ID"),
        sa.Column("sync_status", sa.String(length=64), nullable=False, comment="同步状态"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True, comment="最后同步时间"),
        sa.Column("last_error", sa.Text(), nullable=True, comment="最后错误"),
        sa.Column("retry_count", sa.Integer(), nullable=False, comment="重试次数"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
        sa.UniqueConstraint(
            "enterprise_id",
            "object_type",
            "local_id",
            "external_system",
            name="uq_external_mapping_local",
        ),
        sa.UniqueConstraint("enterprise_id", "external_system", "external_id", name="uq_external_mapping_external"),
    )
    op.create_index("ix_external_id_mappings_enterprise_id", "external_id_mappings", ["enterprise_id"])

    op.create_table(
        "integration_events",
        sa.Column("id", sa.Integer(), primary_key=True, comment="事件 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=True, comment="企业 ID"),
        sa.Column("provider", sa.String(length=64), nullable=False, comment="外部平台"),
        sa.Column("event_type", sa.String(length=128), nullable=False, comment="事件类型"),
        sa.Column("external_event_id", sa.String(length=128), nullable=True, comment="外部事件 ID"),
        sa.Column("payload", sa.JSON(), nullable=False, comment="原始事件内容"),
        sa.Column(
            "status",
            sa.Enum("RECEIVED", "PROCESSING", "SUCCESS", "FAILED", "DUPLICATED", name="integration_event_status"),
            nullable=False,
            comment="处理状态",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, comment="重试次数"),
        sa.Column("last_error", sa.Text(), nullable=True, comment="最后错误"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True, comment="处理完成时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
        sa.UniqueConstraint("provider", "event_type", "external_event_id", name="uq_integration_events_external"),
    )
    op.create_index("ix_integration_events_enterprise_id", "integration_events", ["enterprise_id"])
    op.create_index("ix_integration_events_status", "integration_events", ["status"])
    op.create_index("ix_integration_events_provider_type", "integration_events", ["provider", "event_type"])

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=255), primary_key=True, comment="幂等键"),
        sa.Column("event_type", sa.String(length=128), nullable=False, comment="事件类型"),
        sa.Column("provider", sa.String(length=64), nullable=True, comment="外部平台"),
        sa.Column("result", sa.JSON(), nullable=True, comment="已处理结果"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True, comment="处理时间"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True, comment="过期时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_idempotency_keys_expires_at", "idempotency_keys", ["expires_at"])

    op.create_table(
        "sla_policies",
        sa.Column("id", sa.Integer(), primary_key=True, comment="SLA 策略 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=True, comment="企业 ID"),
        sa.Column("business_type", sa.String(length=64), nullable=False, comment="业务类型"),
        sa.Column("priority", sa.String(length=32), nullable=False, comment="优先级"),
        sa.Column("response_minutes", sa.Integer(), nullable=False, comment="响应时限，分钟"),
        sa.Column("resolve_minutes", sa.Integer(), nullable=False, comment="处理时限，分钟"),
        sa.Column("remind_before_minutes", sa.Integer(), nullable=False, comment="提前提醒分钟数"),
        sa.Column("escalate_after_minutes", sa.Integer(), nullable=False, comment="超时后升级分钟数"),
        sa.Column("escalate_to_role", sa.String(length=64), nullable=True, comment="升级到角色"),
        sa.Column("enabled", sa.Boolean(), nullable=False, comment="是否启用"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
        sa.UniqueConstraint("enterprise_id", "business_type", "priority", name="uq_sla_policy_scope"),
    )
    op.create_index("ix_sla_policies_enterprise_id", "sla_policies", ["enterprise_id"])

    op.create_table(
        "sla_instances",
        sa.Column("id", sa.Integer(), primary_key=True, comment="SLA 实例 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=True, comment="企业 ID"),
        sa.Column("policy_id", sa.Integer(), sa.ForeignKey("sla_policies.id"), nullable=True, comment="SLA 策略 ID"),
        sa.Column("business_type", sa.String(length=64), nullable=False, comment="业务类型"),
        sa.Column("business_id", sa.String(length=64), nullable=False, comment="业务对象 ID"),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "PAUSED", "BREACHED", "RESOLVED", "CANCELLED", name="sla_status"),
            nullable=False,
            comment="SLA 状态",
        ),
        sa.Column("response_due_at", sa.DateTime(timezone=True), nullable=True, comment="响应截止时间"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True, comment="处理截止时间"),
        sa.Column("first_remind_at", sa.DateTime(timezone=True), nullable=True, comment="首次提醒时间"),
        sa.Column("breached_at", sa.DateTime(timezone=True), nullable=True, comment="超时时间"),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True, comment="升级时间"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True, comment="关闭时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_sla_instances_enterprise_id", "sla_instances", ["enterprise_id"])
    op.create_index("ix_sla_instances_policy_id", "sla_instances", ["policy_id"])

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, comment="通知记录 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=True, comment="企业 ID"),
        sa.Column("platform", sa.String(length=64), nullable=False, comment="通知平台"),
        sa.Column("recipient_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, comment="本地接收人 ID"),
        sa.Column("recipient_external_user_id", sa.String(length=128), nullable=True, comment="外部平台接收人 ID"),
        sa.Column("message_type", sa.String(length=64), nullable=False, comment="消息类型"),
        sa.Column("title", sa.String(length=255), nullable=True, comment="消息标题"),
        sa.Column("business_type", sa.String(length=64), nullable=True, comment="关联业务类型"),
        sa.Column("business_id", sa.String(length=64), nullable=True, comment="关联业务 ID"),
        sa.Column(
            "status",
            sa.Enum("PENDING", "SUCCESS", "FAILED", "RETRYING", name="notification_delivery_status"),
            nullable=False,
            comment="发送状态",
        ),
        sa.Column("response_code", sa.Integer(), nullable=True, comment="平台响应码"),
        sa.Column("response_body", sa.Text(), nullable=True, comment="平台响应内容"),
        sa.Column("retryable", sa.Boolean(), nullable=False, comment="是否允许重试"),
        sa.Column("retry_count", sa.Integer(), nullable=False, comment="重试次数"),
        sa.Column("last_error", sa.Text(), nullable=True, comment="最后错误"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True, comment="发送成功时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_notification_deliveries_enterprise_id", "notification_deliveries", ["enterprise_id"])
    op.create_index("ix_notification_deliveries_recipient_user_id", "notification_deliveries", ["recipient_user_id"])

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, comment="用户 ID"),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True, comment="角色 ID"),
        sa.Column("enterprise_id", sa.Integer(), sa.ForeignKey("enterprises.id"), nullable=True, comment="企业 ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
    )
    op.create_index("ix_user_roles_enterprise_id", "user_roles", ["enterprise_id"])


def downgrade() -> None:
    """回滚企业集成基础表。"""
    op.drop_index("ix_user_roles_enterprise_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ix_notification_deliveries_recipient_user_id", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_enterprise_id", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")

    op.drop_index("ix_sla_instances_policy_id", table_name="sla_instances")
    op.drop_index("ix_sla_instances_enterprise_id", table_name="sla_instances")
    op.drop_table("sla_instances")

    op.drop_index("ix_sla_policies_enterprise_id", table_name="sla_policies")
    op.drop_table("sla_policies")

    op.drop_index("ix_idempotency_keys_expires_at", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")

    op.drop_index("ix_integration_events_provider_type", table_name="integration_events")
    op.drop_index("ix_integration_events_status", table_name="integration_events")
    op.drop_index("ix_integration_events_enterprise_id", table_name="integration_events")
    op.drop_table("integration_events")

    op.drop_index("ix_external_id_mappings_enterprise_id", table_name="external_id_mappings")
    op.drop_table("external_id_mappings")

    op.drop_index("ix_integration_configs_enterprise_id", table_name="integration_configs")
    op.drop_table("integration_configs")

    op.drop_index("uq_users_enterprise_external_user", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_index("ix_users_external_user_id", table_name="users")
    op.drop_index("ix_users_enterprise_id", table_name="users")
    op.drop_constraint("fk_users_department_id_departments", "users", type_="foreignkey")
    op.drop_constraint("fk_users_enterprise_id_enterprises", "users", type_="foreignkey")
    for column_name in [
        "is_admin",
        "status",
        "email",
        "mobile_hash",
        "position",
        "department_id",
        "external_user_id",
        "enterprise_id",
    ]:
        op.drop_column("users", column_name)

    op.drop_index("ix_roles_enterprise_id", table_name="roles")
    op.drop_table("roles")

    op.drop_index("ix_departments_parent_id", table_name="departments")
    op.drop_index("ix_departments_enterprise_id", table_name="departments")
    op.drop_table("departments")

    op.drop_index("ix_enterprises_code", table_name="enterprises")
    op.drop_index("ix_enterprises_name", table_name="enterprises")
    op.drop_table("enterprises")

    for enum_name in [
        "notification_delivery_status",
        "sla_status",
        "integration_event_status",
        "integration_config_status",
        "user_status",
        "department_status",
        "enterprise_status",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

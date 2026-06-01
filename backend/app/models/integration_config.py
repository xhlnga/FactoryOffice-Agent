from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IntegrationConfigStatus, TimestampMixin


class IntegrationConfig(TimestampMixin, Base):
    """企业外部系统配置表，密钥字段只保存加密值或密钥引用。"""

    __tablename__ = "integration_configs"
    __table_args__ = (
        UniqueConstraint("enterprise_id", "platform", "name", name="uq_integration_configs_enterprise_platform_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="集成配置 ID")
    enterprise_id: Mapped[int] = mapped_column(ForeignKey("enterprises.id"), index=True, nullable=False, comment="企业 ID")
    platform: Mapped[str] = mapped_column(String(64), nullable=False, comment="平台类型")
    name: Mapped[str] = mapped_column(String(128), default="default", nullable=False, comment="配置名称")
    status: Mapped[IntegrationConfigStatus] = mapped_column(
        Enum(IntegrationConfigStatus, name="integration_config_status"),
        default=IntegrationConfigStatus.DISABLED,
        nullable=False,
        comment="配置状态",
    )
    corp_id: Mapped[str | None] = mapped_column(String(128), comment="企业 ID 或 CorpId")
    app_key: Mapped[str | None] = mapped_column(String(128), comment="应用 Key")
    agent_id: Mapped[str | None] = mapped_column(String(128), comment="应用 AgentId")
    encrypted_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, comment="加密配置或密钥引用")
    webhook_url: Mapped[str | None] = mapped_column(String(512), comment="Webhook 地址")
    callback_url: Mapped[str | None] = mapped_column(String(512), comment="回调地址")
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="最后健康检查时间")
    last_health_status: Mapped[str | None] = mapped_column(String(64), comment="最后健康检查状态")

    enterprise = relationship("Enterprise", back_populates="integration_configs")

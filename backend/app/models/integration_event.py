from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IntegrationEventStatus, TimestampMixin


class IntegrationEvent(TimestampMixin, Base):
    """外部平台回调事件表，用于状态追踪、失败重试和审计排查。"""

    __tablename__ = "integration_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_type", "external_event_id", name="uq_integration_events_external"),
        Index("ix_integration_events_status", "status"),
        Index("ix_integration_events_provider_type", "provider", "event_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="事件 ID")
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id"), index=True, comment="企业 ID")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, comment="外部平台")
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, comment="事件类型")
    external_event_id: Mapped[str | None] = mapped_column(String(128), comment="外部事件 ID")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, comment="原始事件内容")
    status: Mapped[IntegrationEventStatus] = mapped_column(
        Enum(IntegrationEventStatus, name="integration_event_status"),
        default=IntegrationEventStatus.RECEIVED,
        nullable=False,
        comment="处理状态",
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="重试次数")
    last_error: Mapped[str | None] = mapped_column(Text, comment="最后错误")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="处理完成时间")

    enterprise = relationship("Enterprise")

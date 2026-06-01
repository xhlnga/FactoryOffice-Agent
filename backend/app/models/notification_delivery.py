from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, NotificationDeliveryStatus, TimestampMixin


class NotificationDelivery(TimestampMixin, Base):
    """通知发送记录表，记录发送对象、平台响应、失败原因和重试状态。"""

    __tablename__ = "notification_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True, comment="通知记录 ID")
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id"), index=True, comment="企业 ID")
    platform: Mapped[str] = mapped_column(String(64), nullable=False, comment="通知平台")
    recipient_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, comment="本地接收人 ID")
    recipient_external_user_id: Mapped[str | None] = mapped_column(String(128), comment="外部平台接收人 ID")
    message_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="消息类型")
    title: Mapped[str | None] = mapped_column(String(255), comment="消息标题")
    action_url: Mapped[str | None] = mapped_column(String(512), comment="通知跳转链接")
    payload_snapshot: Mapped[dict | None] = mapped_column(JSON, comment="通知内容快照，用于失败重试")
    business_type: Mapped[str | None] = mapped_column(String(64), comment="关联业务类型")
    business_id: Mapped[str | None] = mapped_column(String(64), comment="关联业务 ID")
    status: Mapped[NotificationDeliveryStatus] = mapped_column(
        Enum(NotificationDeliveryStatus, name="notification_delivery_status"),
        default=NotificationDeliveryStatus.PENDING,
        nullable=False,
        comment="发送状态",
    )
    response_code: Mapped[int | None] = mapped_column(Integer, comment="平台响应码")
    response_body: Mapped[str | None] = mapped_column(Text, comment="平台响应内容")
    retryable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否允许重试")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="重试次数")
    last_error: Mapped[str | None] = mapped_column(Text, comment="最后错误")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="发送成功时间")

    enterprise = relationship("Enterprise")
    recipient = relationship("User", back_populates="notification_deliveries")

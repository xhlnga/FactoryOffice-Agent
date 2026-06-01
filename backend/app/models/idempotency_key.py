from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class IdempotencyKey(TimestampMixin, Base):
    """幂等键表，防止重复回调、重复审批和重复写入外部系统。"""

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(255), primary_key=True, comment="幂等键")
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, comment="事件类型")
    provider: Mapped[str | None] = mapped_column(String(64), comment="外部平台")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="已处理结果")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="处理时间")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, comment="过期时间")

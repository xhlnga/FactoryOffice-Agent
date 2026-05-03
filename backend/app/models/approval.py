from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ApprovalStatus, Base, TimestampMixin


class Approval(TimestampMixin, Base):
    """审批表，保存 Agent 建议执行但需要人工确认的动作。"""

    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True, comment="审批 ID")
    action_type: Mapped[str] = mapped_column(String(128), nullable=False, comment="动作类型")
    action_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, comment="动作参数")
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"),
        default=ApprovalStatus.PENDING,
        nullable=False,
        comment="审批状态",
    )
    reviewer: Mapped[str | None] = mapped_column(String(128), comment="审批人")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="审批时间")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="执行时间")
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="执行结果")
    comment: Mapped[str | None] = mapped_column(String(512), comment="审批意见")

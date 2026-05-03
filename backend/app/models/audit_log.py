from typing import Any

from sqlalchemy import Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditStatus, Base, TimestampMixin


class AuditLog(TimestampMixin, Base):
    """审计日志表，记录用户输入、模型输出、工具调用和执行结果。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, comment="审计日志 ID")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), comment="用户 ID")
    action: Mapped[str] = mapped_column(String(128), nullable=False, comment="动作名称")
    input: Mapped[str | None] = mapped_column(Text, comment="用户输入")
    output: Mapped[str | None] = mapped_column(Text, comment="模型或工具输出")
    tool_name: Mapped[str | None] = mapped_column(String(128), comment="工具名称")
    tool_args: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="工具参数")
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, name="audit_status"),
        default=AuditStatus.PENDING,
        nullable=False,
        comment="执行状态",
    )

    user = relationship("User", back_populates="audit_logs")


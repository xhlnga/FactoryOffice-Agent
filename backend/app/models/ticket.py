from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TaskPriority, TicketStatus, TimestampMixin


class Ticket(TimestampMixin, Base):
    """工单表，用于设备维修、质量异常等流程。"""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, comment="工单 ID")
    ticket_type: Mapped[str] = mapped_column(String(64), default="设备维修", nullable=False, comment="工单类型")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="工单标题")
    description: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="工单描述")
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="ticket_priority"),
        default=TaskPriority.MEDIUM,
        nullable=False,
        comment="优先级",
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"),
        default=TicketStatus.OPEN,
        nullable=False,
        comment="工单状态",
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), comment="创建人 ID")

    creator = relationship("User", back_populates="tickets")


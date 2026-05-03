from datetime import date

from sqlalchemy import Date, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TaskPriority, TaskStatus, TimestampMixin


class Task(TimestampMixin, Base):
    """任务表，用于会议纪要转任务和人工确认后的任务写入。"""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, comment="任务 ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="任务标题")
    description: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="任务描述")
    assignee: Mapped[str | None] = mapped_column(String(128), comment="负责人")
    due_date: Mapped[date | None] = mapped_column(Date, comment="截止日期")
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority"),
        default=TaskPriority.MEDIUM,
        nullable=False,
        comment="优先级",
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"),
        default=TaskStatus.TODO,
        nullable=False,
        comment="任务状态",
    )
    source: Mapped[str | None] = mapped_column(String(128), comment="任务来源")


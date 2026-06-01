from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ApprovalInstanceStatus, Base, TimestampMixin


class ApprovalInstance(TimestampMixin, Base):
    """审批实例，表示某个业务对象正在按模板流转。"""

    __tablename__ = "approval_instances"

    id: Mapped[int] = mapped_column(primary_key=True, comment="审批实例 ID")
    template_id: Mapped[int | None] = mapped_column(ForeignKey("approval_templates.id"), index=True, comment="审批模板 ID")
    approval_id: Mapped[int | None] = mapped_column(ForeignKey("approvals.id"), index=True, comment="兼容审批 ID")
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id"), index=True, comment="企业 ID")
    business_type: Mapped[str] = mapped_column(String(128), nullable=False, comment="业务类型")
    business_id: Mapped[str | None] = mapped_column(String(64), comment="业务对象 ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="审批标题")
    status: Mapped[ApprovalInstanceStatus] = mapped_column(
        Enum(ApprovalInstanceStatus, name="approval_instance_status"),
        default=ApprovalInstanceStatus.PENDING,
        nullable=False,
        comment="审批实例状态",
    )
    current_step_order: Mapped[int | None] = mapped_column(Integer, comment="当前步骤顺序")
    created_by: Mapped[str | None] = mapped_column(String(128), comment="发起人")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="完成时间")
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="撤回时间")

    template = relationship("ApprovalTemplate", back_populates="instances")
    approval = relationship("Approval", back_populates="approval_instances")
    enterprise = relationship("Enterprise")
    steps = relationship(
        "ApprovalInstanceStep",
        back_populates="instance",
        cascade="all, delete-orphan",
        order_by="ApprovalInstanceStep.step_order",
    )
    actions = relationship("ApprovalAction", back_populates="instance", cascade="all, delete-orphan")

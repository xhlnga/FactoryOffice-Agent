from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ApprovalStepMode, ApprovalStepStatus, ApproverType, Base, TimestampMixin


class ApprovalInstanceStep(TimestampMixin, Base):
    """审批实例步骤，是模板步骤在某次审批中的快照。"""

    __tablename__ = "approval_instance_steps"

    id: Mapped[int] = mapped_column(primary_key=True, comment="审批实例步骤 ID")
    instance_id: Mapped[int] = mapped_column(
        ForeignKey("approval_instances.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="审批实例 ID",
    )
    template_step_id: Mapped[int | None] = mapped_column(ForeignKey("approval_steps.id"), comment="模板步骤 ID")
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="步骤顺序")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="步骤名称")
    approver_type: Mapped[ApproverType] = mapped_column(
        Enum(ApproverType, name="approver_type"),
        nullable=False,
        comment="审批人选择方式",
    )
    approver_value: Mapped[str] = mapped_column(String(128), nullable=False, comment="审批人、角色或表达式")
    assigned_to: Mapped[str | None] = mapped_column(String(128), comment="当前处理人或角色")
    mode: Mapped[ApprovalStepMode] = mapped_column(
        Enum(ApprovalStepMode, name="approval_step_mode"),
        default=ApprovalStepMode.ANY,
        nullable=False,
        comment="会签/或签模式",
    )
    status: Mapped[ApprovalStepStatus] = mapped_column(
        Enum(ApprovalStepStatus, name="approval_step_status"),
        default=ApprovalStepStatus.PENDING,
        nullable=False,
        comment="步骤状态",
    )
    timeout_hours: Mapped[int | None] = mapped_column(Integer, comment="超时小时数")
    escalate_to: Mapped[str | None] = mapped_column(String(128), comment="超时升级到角色或人员")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="批准时间")
    comment: Mapped[str | None] = mapped_column(String(512), comment="审批意见")

    instance = relationship("ApprovalInstance", back_populates="steps")
    template_step = relationship("ApprovalStep", back_populates="instance_steps")
    actions = relationship("ApprovalAction", back_populates="step")

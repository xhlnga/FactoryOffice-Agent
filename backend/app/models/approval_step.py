from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ApprovalStepMode, ApproverType, Base, TimestampMixin


class ApprovalStep(TimestampMixin, Base):
    """审批模板步骤，定义步骤顺序、审批人来源、会签/或签模式和超时升级规则。"""

    __tablename__ = "approval_steps"

    id: Mapped[int] = mapped_column(primary_key=True, comment="审批步骤 ID")
    template_id: Mapped[int] = mapped_column(
        ForeignKey("approval_templates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="审批模板 ID",
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="步骤顺序")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="步骤名称")
    approver_type: Mapped[ApproverType] = mapped_column(
        Enum(ApproverType, name="approver_type"),
        nullable=False,
        comment="审批人选择方式",
    )
    approver_value: Mapped[str] = mapped_column(String(128), nullable=False, comment="审批人、角色或表达式")
    mode: Mapped[ApprovalStepMode] = mapped_column(
        Enum(ApprovalStepMode, name="approval_step_mode"),
        default=ApprovalStepMode.ANY,
        nullable=False,
        comment="会签/或签模式",
    )
    timeout_hours: Mapped[int | None] = mapped_column(Integer, comment="超时小时数")
    escalate_to: Mapped[str | None] = mapped_column(String(128), comment="超时升级到角色或人员")

    template = relationship("ApprovalTemplate", back_populates="steps")
    instance_steps = relationship("ApprovalInstanceStep", back_populates="template_step")

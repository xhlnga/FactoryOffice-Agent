from typing import Any

from sqlalchemy import Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ApprovalActionType, Base, TimestampMixin


class ApprovalAction(TimestampMixin, Base):
    """审批动作日志，记录批准、拒绝、转交、撤回、升级等操作。"""

    __tablename__ = "approval_actions"

    id: Mapped[int] = mapped_column(primary_key=True, comment="审批动作 ID")
    instance_id: Mapped[int] = mapped_column(
        ForeignKey("approval_instances.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="审批实例 ID",
    )
    step_id: Mapped[int | None] = mapped_column(ForeignKey("approval_instance_steps.id"), index=True, comment="审批步骤 ID")
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, comment="操作人用户 ID")
    actor_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="操作人名称")
    action: Mapped[ApprovalActionType] = mapped_column(
        Enum(ApprovalActionType, name="approval_action_type"),
        nullable=False,
        comment="审批动作",
    )
    comment: Mapped[str | None] = mapped_column(String(512), comment="操作意见")
    from_approver: Mapped[str | None] = mapped_column(String(128), comment="转交前处理人")
    to_approver: Mapped[str | None] = mapped_column(String(128), comment="转交后处理人")
    action_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, comment="动作元数据")

    instance = relationship("ApprovalInstance", back_populates="actions")
    step = relationship("ApprovalInstanceStep", back_populates="actions")
    actor = relationship("User")

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ApprovalTemplateStatus, Base, TimestampMixin


class ApprovalTemplate(TimestampMixin, Base):
    """审批模板，定义某类业务动作应走哪条审批流。"""

    __tablename__ = "approval_templates"
    __table_args__ = (
        Index("ix_approval_templates_business_enabled", "business_type", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="审批模板 ID")
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id"), index=True, comment="企业 ID")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    business_type: Mapped[str] = mapped_column(String(128), nullable=False, comment="业务类型或动作类型")
    description: Mapped[str | None] = mapped_column(Text, comment="模板说明")
    min_amount: Mapped[float | None] = mapped_column(Float, comment="适用最小金额，含边界")
    max_amount: Mapped[float | None] = mapped_column(Float, comment="适用最大金额，不含边界")
    status: Mapped[ApprovalTemplateStatus] = mapped_column(
        Enum(ApprovalTemplateStatus, name="approval_template_status"),
        default=ApprovalTemplateStatus.ENABLED,
        nullable=False,
        comment="模板状态",
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否默认模板")

    enterprise = relationship("Enterprise")
    steps = relationship(
        "ApprovalStep",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ApprovalStep.step_order",
    )
    instances = relationship("ApprovalInstance", back_populates="template")

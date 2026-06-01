from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SLAStatus, TimestampMixin


class SLAPolicyModel(TimestampMixin, Base):
    """SLA 策略表，定义不同业务类型和优先级的响应/处理时限。"""

    __tablename__ = "sla_policies"
    __table_args__ = (UniqueConstraint("enterprise_id", "business_type", "priority", name="uq_sla_policy_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True, comment="SLA 策略 ID")
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id"), index=True, comment="企业 ID")
    business_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="业务类型")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, comment="优先级")
    response_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False, comment="响应时限，分钟")
    resolve_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False, comment="处理时限，分钟")
    remind_before_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False, comment="提前提醒分钟数")
    escalate_after_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="超时后升级分钟数")
    escalate_to_role: Mapped[str | None] = mapped_column(String(64), comment="升级到角色")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")

    enterprise = relationship("Enterprise")
    instances = relationship("SLAInstance", back_populates="policy")


class SLAInstance(TimestampMixin, Base):
    """SLA 实例表，绑定具体业务对象并记录提醒、超时和关闭状态。"""

    __tablename__ = "sla_instances"

    id: Mapped[int] = mapped_column(primary_key=True, comment="SLA 实例 ID")
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id"), index=True, comment="企业 ID")
    policy_id: Mapped[int | None] = mapped_column(ForeignKey("sla_policies.id"), index=True, comment="SLA 策略 ID")
    business_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="业务类型")
    business_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="业务对象 ID")
    status: Mapped[SLAStatus] = mapped_column(
        Enum(SLAStatus, name="sla_status"),
        default=SLAStatus.ACTIVE,
        nullable=False,
        comment="SLA 状态",
    )
    response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="响应截止时间")
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="处理截止时间")
    first_remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="首次提醒时间")
    breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="超时时间")
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="升级时间")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="关闭时间")

    enterprise = relationship("Enterprise")
    policy = relationship("SLAPolicyModel", back_populates="instances")

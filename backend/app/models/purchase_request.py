from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PurchaseStatus, TimestampMixin


class PurchaseRequest(TimestampMixin, Base):
    """采购申请表，用于保存人工确认后的采购申请。"""

    __tablename__ = "purchase_requests"

    id: Mapped[int] = mapped_column(primary_key=True, comment="采购申请 ID")
    item_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="物品名称")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="数量")
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="采购原因")
    budget: Mapped[float | None] = mapped_column(Float, comment="预算金额")
    supplier: Mapped[str | None] = mapped_column(String(255), comment="供应商")
    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, name="purchase_status"),
        default=PurchaseStatus.DRAFT,
        nullable=False,
        comment="采购状态",
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), comment="创建人 ID")

    creator = relationship("User", back_populates="purchase_requests")


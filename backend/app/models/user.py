from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UserRole


class User(TimestampMixin, Base):
    """用户表，当前用于本地身份模拟和后续权限扩展。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, comment="用户 ID")
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="用户名")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.EMPLOYEE,
        nullable=False,
        comment="用户角色",
    )
    department: Mapped[str | None] = mapped_column(String(128), comment="所属部门")

    documents = relationship("Document", back_populates="uploader")
    tickets = relationship("Ticket", back_populates="creator")
    purchase_requests = relationship("PurchaseRequest", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="user")


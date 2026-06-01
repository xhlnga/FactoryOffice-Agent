from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Role(TimestampMixin, Base):
    """企业角色表，用于采购、质量、设备、财务等业务角色扩展。"""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("enterprise_id", "code", name="uq_roles_enterprise_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, comment="角色 ID")
    enterprise_id: Mapped[int] = mapped_column(ForeignKey("enterprises.id"), index=True, nullable=False, comment="企业 ID")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="角色编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="角色名称")
    description: Mapped[str | None] = mapped_column(Text, comment="角色说明")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否系统内置角色")

    enterprise = relationship("Enterprise", back_populates="roles")
    user_links = relationship("UserRoleBinding", back_populates="role", cascade="all, delete-orphan")

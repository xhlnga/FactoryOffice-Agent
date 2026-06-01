from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UserRoleBinding(TimestampMixin, Base):
    """用户和企业角色的多对多关系。"""

    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, comment="用户 ID")
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True, comment="角色 ID")
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id"), index=True, comment="企业 ID")

    user = relationship("User", back_populates="role_links")
    role = relationship("Role", back_populates="user_links")
    enterprise = relationship("Enterprise")

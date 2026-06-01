from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, DepartmentStatus, TimestampMixin


class Department(TimestampMixin, Base):
    """企业部门表，保留外部平台部门 ID，支持父子部门和组织同步。"""

    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("enterprise_id", "external_department_id", name="uq_departments_enterprise_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="部门 ID")
    enterprise_id: Mapped[int] = mapped_column(ForeignKey("enterprises.id"), index=True, nullable=False, comment="企业 ID")
    external_department_id: Mapped[str | None] = mapped_column(String(128), comment="外部平台部门 ID")
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), index=True, comment="上级部门 ID")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="部门名称")
    path: Mapped[str | None] = mapped_column(String(512), comment="部门路径")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序值")
    status: Mapped[DepartmentStatus] = mapped_column(
        Enum(DepartmentStatus, name="department_status"),
        default=DepartmentStatus.ACTIVE,
        nullable=False,
        comment="部门状态",
    )

    enterprise = relationship("Enterprise", back_populates="departments")
    parent = relationship("Department", remote_side=[id], back_populates="children")
    children = relationship("Department", back_populates="parent")
    users = relationship("User", back_populates="department_ref", foreign_keys="User.department_id")

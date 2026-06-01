from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UserRole, UserStatus


class User(TimestampMixin, Base):
    """用户表，兼容本地演示登录、组织同步和权限扩展。"""

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
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id"), index=True, comment="所属企业 ID")
    external_user_id: Mapped[str | None] = mapped_column(String(128), index=True, comment="外部平台用户 ID")
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), index=True, comment="部门 ID")
    position: Mapped[str | None] = mapped_column(String(128), comment="岗位")
    mobile_hash: Mapped[str | None] = mapped_column(String(128), comment="手机号哈希")
    email: Mapped[str | None] = mapped_column(String(255), index=True, comment="邮箱")
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        default=UserStatus.ACTIVE,
        nullable=False,
        comment="账号状态",
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否系统管理员")

    enterprise = relationship("Enterprise", back_populates="users")
    department_ref = relationship("Department", back_populates="users", foreign_keys=[department_id])
    role_links = relationship("UserRoleBinding", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="uploader")
    tickets = relationship("Ticket", back_populates="creator")
    purchase_requests = relationship("PurchaseRequest", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="user")
    notification_deliveries = relationship("NotificationDelivery", back_populates="recipient")
    created_document_permissions = relationship(
        "DocumentPermission",
        back_populates="creator",
        foreign_keys="DocumentPermission.created_by",
    )

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DocumentPermission(TimestampMixin, Base):
    """文档权限表。

    企业知识库不能只按“是否登录”控制访问，制度、采购、质量、安全资料都需要按人、部门或角色授权。
    """

    __tablename__ = "document_permissions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "principal_type",
            "principal_id",
            "permission",
            name="uq_document_permissions_scope",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="文档权限 ID")
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="文档 ID",
    )
    enterprise_id: Mapped[int | None] = mapped_column(
        ForeignKey("enterprises.id"),
        index=True,
        comment="企业 ID",
    )
    principal_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False, comment="授权主体类型")
    principal_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False, comment="授权主体 ID")
    permission: Mapped[str] = mapped_column(String(32), default="view", nullable=False, comment="权限动作")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), comment="授权创建人")

    document = relationship("Document", back_populates="permissions")
    enterprise = relationship("Enterprise")
    creator = relationship("User", back_populates="created_document_permissions", foreign_keys=[created_by])

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Document(TimestampMixin, Base):
    """文档表，保存上传文件的基础信息。"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, comment="文档 ID")
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="文档标题")
    category: Mapped[str] = mapped_column(String(64), default="未分类", nullable=False, comment="文档分类")
    file_path: Mapped[str | None] = mapped_column(String(512), comment="本地文件路径")
    content_type: Mapped[str | None] = mapped_column(String(128), comment="文件 MIME 类型")
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, comment="文件大小，单位字节")
    file_sha256: Mapped[str | None] = mapped_column(String(64), index=True, comment="文件 SHA-256 摘要")
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), comment="上传人 ID")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, comment="软删除时间")

    uploader = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

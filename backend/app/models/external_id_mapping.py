from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ExternalIdMapping(TimestampMixin, Base):
    """本地业务对象和外部系统对象 ID 的映射关系。"""

    __tablename__ = "external_id_mappings"
    __table_args__ = (
        UniqueConstraint(
            "enterprise_id",
            "object_type",
            "local_id",
            "external_system",
            name="uq_external_mapping_local",
        ),
        UniqueConstraint("enterprise_id", "external_system", "external_id", name="uq_external_mapping_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="映射 ID")
    enterprise_id: Mapped[int | None] = mapped_column(ForeignKey("enterprises.id"), index=True, comment="企业 ID")
    object_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="本地对象类型")
    local_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="本地对象 ID")
    external_system: Mapped[str] = mapped_column(String(64), nullable=False, comment="外部系统")
    external_id: Mapped[str | None] = mapped_column(String(128), comment="外部对象 ID")
    sync_status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False, comment="同步状态")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="最后同步时间")
    last_error: Mapped[str | None] = mapped_column(Text, comment="最后错误")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="重试次数")

    enterprise = relationship("Enterprise")

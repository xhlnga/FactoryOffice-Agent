from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, EnterpriseStatus, TimestampMixin


class Enterprise(TimestampMixin, Base):
    """企业/租户表，用于企业集成配置归属，并支撑逐步多企业隔离。"""

    __tablename__ = "enterprises"

    id: Mapped[int] = mapped_column(primary_key=True, comment="企业 ID")
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="企业名称")
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="企业编码")
    status: Mapped[EnterpriseStatus] = mapped_column(
        Enum(EnterpriseStatus, name="enterprise_status"),
        default=EnterpriseStatus.ACTIVE,
        nullable=False,
        comment="企业状态",
    )

    users = relationship("User", back_populates="enterprise")
    departments = relationship("Department", back_populates="enterprise")
    roles = relationship("Role", back_populates="enterprise")
    integration_configs = relationship("IntegrationConfig", back_populates="enterprise")

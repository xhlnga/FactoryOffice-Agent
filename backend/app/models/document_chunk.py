from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType

from app.models.base import Base, TimestampMixin


class Vector(UserDefinedType):
    """pgvector 字段类型。

    这里不额外引入 Python pgvector 包，先声明数据库列类型。
    数据库迁移时需要先执行：CREATE EXTENSION IF NOT EXISTS vector;
    """

    cache_ok = True

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_: Any) -> str:
        return f"vector({self.dimensions})"

    def bind_processor(self, dialect):  # noqa: ANN001
        """把 Python list 转成 pgvector 可接收的字符串。"""

        def process(value: list[float] | str | None) -> str | None:
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return "[" + ",".join(str(float(item)) for item in value) + "]"

        return process

    def result_processor(self, dialect, coltype):  # noqa: ANN001
        """读取向量时尽量转回 float 列表，方便后续调试。"""

        def process(value: str | list[float] | None) -> list[float] | None:
            if value is None or isinstance(value, list):
                return value
            return [float(item) for item in value.strip("[]").split(",") if item]

        return process


class DocumentChunk(TimestampMixin, Base):
    """文档切块表，保存切块文本、向量和检索元数据。"""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, comment="切块 ID")
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, comment="文档 ID")
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False, comment="切块文本")
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="切块序号")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), comment="文档切块向量")
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False, comment="切块元数据")

    document = relationship("Document", back_populates="chunks")

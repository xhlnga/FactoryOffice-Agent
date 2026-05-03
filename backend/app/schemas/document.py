from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DocumentBase(BaseModel):
    """文档基础字段。"""

    filename: str = Field(..., min_length=1, max_length=255, description="文件名")
    title: str = Field(..., min_length=1, max_length=255, description="文档标题")
    category: str = Field(default="未分类", max_length=64, description="文档分类")


class DocumentCreate(DocumentBase):
    """创建文档记录请求。"""

    file_path: str | None = Field(default=None, max_length=512, description="文件路径")
    content_type: str | None = Field(default=None, max_length=128, description="文件类型")
    file_size_bytes: int | None = Field(default=None, ge=0, description="文件大小，单位字节")
    file_sha256: str | None = Field(default=None, min_length=64, max_length=64, description="文件 SHA-256")
    uploaded_by: int | None = Field(default=None, description="上传人 ID")


class DocumentRead(DocumentBase, ORMModel):
    """文档响应结构。"""

    id: int = Field(..., description="文档 ID")
    content_type: str | None = Field(default=None, description="文件类型")
    file_size_bytes: int | None = Field(default=None, description="文件大小，单位字节")
    file_sha256: str | None = Field(default=None, description="文件 SHA-256")
    uploaded_by: int | None = Field(default=None, description="上传人 ID")
    deleted_at: datetime | None = Field(default=None, description="软删除时间")
    created_at: datetime = Field(..., description="创建时间")


class DocumentUploadResponse(BaseModel):
    """文档上传响应结构。"""

    filename: str | None = Field(default=None, description="文件名")
    content_type: str | None = Field(default=None, description="文件类型")
    category: str = Field(..., description="文档分类")
    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="说明信息")


class DocumentChunkRead(ORMModel):
    """文档切块响应结构。"""

    id: int = Field(..., description="切块 ID")
    document_id: int = Field(..., description="文档 ID")
    chunk_text: str = Field(..., description="切块文本")
    chunk_index: int = Field(..., description="切块序号")
    chunk_metadata: dict[str, Any] = Field(default_factory=dict, description="切块元数据")
    created_at: datetime = Field(..., description="创建时间")

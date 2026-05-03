from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ORMModel(BaseModel):
    """允许从 SQLAlchemy 对象转换为响应结构。"""

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """通用消息响应。"""

    message: str = Field(..., description="响应消息")


class IDResponse(MessageResponse):
    """通用 ID 响应。"""

    id: int = Field(..., description="资源 ID")


class PageParams(BaseModel):
    """分页请求参数。"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class PageResponse(BaseModel, Generic[T]):
    """分页响应结构。"""

    items: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, ge=0, description="总数量")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, description="每页数量")


class ErrorResponse(BaseModel):
    """统一错误响应结构。"""

    success: bool = Field(default=False, description="是否成功")
    error_code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误说明")
    details: object | None = Field(default=None, description="错误详情")


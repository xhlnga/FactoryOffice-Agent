from datetime import datetime

from pydantic import BaseModel, Field

from app.models.base import PurchaseStatus
from app.schemas.common import ORMModel


class PurchaseBase(BaseModel):
    """采购申请基础字段。"""

    item_name: str = Field(..., min_length=1, max_length=255, description="物品名称")
    quantity: int = Field(..., ge=1, description="数量")
    reason: str = Field(default="", description="采购原因")
    budget: float | None = Field(default=None, ge=0, description="预算金额")
    supplier: str | None = Field(default=None, max_length=255, description="供应商")


class PurchaseCreateRequest(PurchaseBase):
    """创建采购申请请求。"""

    created_by: int | None = Field(default=None, description="创建人 ID")


class PurchaseUpdateRequest(BaseModel):
    """更新采购申请请求。"""

    item_name: str | None = Field(default=None, min_length=1, max_length=255, description="物品名称")
    quantity: int | None = Field(default=None, ge=1, description="数量")
    reason: str | None = Field(default=None, description="采购原因")
    budget: float | None = Field(default=None, ge=0, description="预算金额")
    supplier: str | None = Field(default=None, max_length=255, description="供应商")
    status: PurchaseStatus | None = Field(default=None, description="采购状态")


class PurchaseRead(PurchaseBase, ORMModel):
    """采购申请响应结构。"""

    id: int = Field(..., description="采购申请 ID")
    status: PurchaseStatus = Field(..., description="采购状态")
    created_by: int | None = Field(default=None, description="创建人 ID")
    created_at: datetime = Field(..., description="创建时间")


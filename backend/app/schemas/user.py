from datetime import datetime

from pydantic import BaseModel, Field

from app.models.base import UserRole
from app.schemas.common import ORMModel


class UserBase(BaseModel):
    """用户基础字段。"""

    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    role: UserRole = Field(default=UserRole.EMPLOYEE, description="用户角色")
    department: str | None = Field(default=None, max_length=128, description="所属部门")


class UserCreate(UserBase):
    """创建用户请求。"""


class UserUpdate(BaseModel):
    """更新用户请求。"""

    role: UserRole | None = Field(default=None, description="用户角色")
    department: str | None = Field(default=None, max_length=128, description="所属部门")


class UserRead(UserBase, ORMModel):
    """用户响应结构。"""

    id: int = Field(..., description="用户 ID")
    created_at: datetime = Field(..., description="创建时间")


class LoginRequest(BaseModel):
    """本地身份模拟登录请求。"""

    username: str = Field(..., min_length=1, description="用户名")
    role: UserRole = Field(default=UserRole.EMPLOYEE, description="用户角色")
    department: str = Field(default="生产部", description="所属部门")


class LoginResponse(BaseModel):
    """本地身份模拟登录响应。"""

    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: UserRead | dict = Field(..., description="用户信息")
    message: str = Field(..., description="说明信息")


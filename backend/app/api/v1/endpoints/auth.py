from fastapi import APIRouter

from app.schemas.user import LoginRequest

router = APIRouter()


@router.post("/login", summary="用户身份模拟登录")
def login(request: LoginRequest) -> dict:
    """返回一个本地模拟身份，后续可替换为真实认证。"""
    return {
        "access_token": "local-dev-token",
        "token_type": "bearer",
        "user": {
            "username": request.username,
            "role": request.role,
            "department": request.department,
        },
        "message": "当前为本地身份模拟，后续接入正式认证与权限体系。",
    }


@router.get("/me", summary="获取当前模拟用户")
def get_current_user() -> dict:
    """提供默认用户信息，便于前端在未接入登录时联调。"""
    return {
        "username": "demo_employee",
        "role": "employee",
        "department": "生产部",
    }

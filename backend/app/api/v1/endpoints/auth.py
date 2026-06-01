from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, create_session_token, get_current_user_optional
from app.schemas.user import LoginRequest

router = APIRouter()


@router.post("/login", summary="本地演示登录")
def login(request: LoginRequest) -> dict:
    """返回本地演示 token，企业接入时可替换为 SSO/OAuth 登录。"""
    access_token = create_session_token(
        {
            "username": request.username,
            "role": request.role.value,
            "department": request.department,
        }
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": request.username,
            "role": request.role,
            "department": request.department,
        },
        "message": "当前使用本地演示登录，企业接入时可替换为 SSO、企业微信、钉钉或飞书登录。",
    }


@router.get("/me", summary="获取当前用户")
def get_current_user(current_user: AuthenticatedUser = Depends(get_current_user_optional)) -> dict:
    """返回当前请求身份；未登录时返回本地演示默认身份。"""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username or "demo_employee",
        "role": current_user.role.value,
        "enterprise_id": current_user.enterprise_id,
        "department_id": current_user.department_id,
        "department": current_user.department or "生产部",
        "role_codes": list(current_user.effective_role_codes),
        "is_admin": current_user.is_admin,
        "auth_source": current_user.auth_source,
    }

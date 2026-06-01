import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, status

from app.core.config import settings
from app.core.security import UserRole, parse_role


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """请求中的用户身份。

    当前同时支持两种方式：
    1. Authorization: Bearer <本系统签发的轻量 token>
    2. X-User-* 请求头，保留本地演示兼容。
    """

    user_id: int | None = None
    username: str | None = None
    role: UserRole = UserRole.EMPLOYEE
    enterprise_id: int | None = None
    department_id: int | None = None
    department: str | None = None
    role_codes: tuple[str, ...] = field(default_factory=tuple)
    is_admin: bool = False
    auth_source: str = "local-header"

    @property
    def effective_role_codes(self) -> tuple[str, ...]:
        """返回去重后的角色编码，兼容简单角色和企业角色。"""
        codes = [self.role.value, *self.role_codes]
        if self.is_admin and UserRole.ADMIN.value not in codes:
            codes.append(UserRole.ADMIN.value)
        return tuple(dict.fromkeys(code for code in codes if code))


def create_session_token(payload: dict[str, Any], *, expires_minutes: int = 480) -> str:
    """签发本地会话 token。

    这里不引入额外 JWT 依赖，便于开源项目开箱运行；生产环境可以替换为企业 SSO/JWT。
    """
    token_payload = {
        **payload,
        "exp": int(time.time()) + expires_minutes * 60,
    }
    payload_part = _base64url_encode(_json_bytes(token_payload))
    signature = _sign(payload_part)
    return f"{payload_part}.{signature}"


def decode_session_token(token: str) -> dict[str, Any]:
    """校验并解析本地会话 token。"""
    try:
        payload_part, signature = token.split(".", 1)
    except ValueError as exc:
        raise _unauthorized("访问令牌格式不正确。") from exc

    if not hmac.compare_digest(_sign(payload_part), signature):
        raise _unauthorized("访问令牌签名校验失败。")

    try:
        payload = json.loads(_base64url_decode(payload_part).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise _unauthorized("访问令牌内容无法解析。") from exc

    expires_at = int(payload.get("exp") or 0)
    if expires_at and expires_at < int(time.time()):
        raise _unauthorized("访问令牌已过期。")
    return payload


def get_current_user_optional(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_id: Annotated[int | None, Header(alias="X-User-Id")] = None,
    x_username: Annotated[str | None, Header(alias="X-Username")] = None,
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    x_enterprise_id: Annotated[int | None, Header(alias="X-Enterprise-Id")] = None,
    x_department_id: Annotated[int | None, Header(alias="X-Department-Id")] = None,
    x_department: Annotated[str | None, Header(alias="X-Department")] = None,
    x_role_codes: Annotated[str | None, Header(alias="X-Role-Codes")] = None,
) -> AuthenticatedUser:
    """读取当前用户。

    未登录时返回普通员工身份，保证本地演示仍能直接访问公开资料。
    """
    if authorization and authorization.lower().startswith("bearer "):
        payload = decode_session_token(authorization.split(" ", 1)[1].strip())
        return _user_from_payload(payload)

    role = parse_role(x_user_role)
    role_codes = _split_role_codes(x_role_codes)
    return AuthenticatedUser(
        user_id=x_user_id,
        username=x_username,
        role=role,
        enterprise_id=x_enterprise_id,
        department_id=x_department_id,
        department=x_department,
        role_codes=role_codes,
        is_admin=role == UserRole.ADMIN,
        auth_source="local-header",
    )


def get_current_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_optional)],
) -> AuthenticatedUser:
    """需要明确登录态的依赖。"""
    if current_user is None or (current_user.user_id is None and current_user.username is None):
        raise _unauthorized("当前接口需要登录后访问。")
    return current_user


def _user_from_payload(payload: dict[str, Any]) -> AuthenticatedUser:
    """从 token payload 构造用户身份。"""
    role = parse_role(str(payload.get("role") or UserRole.EMPLOYEE.value))
    return AuthenticatedUser(
        user_id=_int_or_none(payload.get("user_id")),
        username=payload.get("username"),
        role=role,
        enterprise_id=_int_or_none(payload.get("enterprise_id")),
        department_id=_int_or_none(payload.get("department_id")),
        department=payload.get("department"),
        role_codes=_split_role_codes(payload.get("role_codes")),
        is_admin=bool(payload.get("is_admin")) or role == UserRole.ADMIN,
        auth_source="token",
    )


def _split_role_codes(value: Any) -> tuple[str, ...]:
    """解析角色编码，支持逗号字符串或列表。"""
    if value is None:
        return ()
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]
    return tuple(dict.fromkeys(str(item).strip() for item in items if str(item).strip()))


def _int_or_none(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload_part: str) -> str:
    digest = hmac.new(settings.auth_secret_key.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    return _base64url_encode(digest)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

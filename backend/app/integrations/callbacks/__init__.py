from dataclasses import dataclass
from typing import Any

from app.integrations.core.schemas import ApprovalCallbackEvent, IntegrationPlatform


@dataclass(frozen=True)
class CallbackResult:
    """外部平台回调处理结果。

    response_body 可直接作为回调接口响应体；needs_decryption=True 表示当前事件
    需要平台加解密 SDK 或专用加密库进一步处理，不能当成明文事件执行业务动作。
    """

    platform: IntegrationPlatform
    event_type: str
    payload: dict[str, Any]
    event_id: str | None = None
    duplicated: bool = False
    needs_decryption: bool = False
    response_body: str | dict[str, Any] | None = None
    message: str = ""
    approval_event: ApprovalCallbackEvent | None = None


__all__ = ["CallbackResult"]

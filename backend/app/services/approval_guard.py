from fastapi import status

from app.core.exceptions import AppException


def ensure_approved_action(action_name: str, approved_action: bool) -> None:
    """保护高影响业务写入，避免绕过人工确认直接落库。"""
    if approved_action:
        return
    raise AppException(
        f"{action_name} 必须来自审批通过后的执行流程，不能直接写入业务系统。",
        status_code=status.HTTP_403_FORBIDDEN,
    )

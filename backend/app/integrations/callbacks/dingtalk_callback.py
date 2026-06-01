from typing import Any

from app.integrations.callbacks import CallbackResult
from app.integrations.core.exceptions import IntegrationCallbackVerificationError
from app.integrations.core.idempotency import InMemoryIdempotencyStore, build_idempotency_key
from app.integrations.core.schemas import (
    ApprovalCallbackAction,
    ApprovalCallbackEvent,
    IntegrationPlatform,
)


class DingTalkCallbackHandler:
    """钉钉回调处理器。

    钉钉事件来源很多，包括事件订阅、审批事件、机器人交互等。正式生产建议使用
    钉钉开放平台 SDK 处理加解密和 ACK；当前处理器只处理明文事件标准化、可选
    token 校验、幂等和内部审批事件映射。
    """

    platform = IntegrationPlatform.DINGTALK

    def __init__(
        self,
        *,
        callback_token: str | None = None,
        idempotency_store: InMemoryIdempotencyStore | None = None,
    ) -> None:
        self.callback_token = callback_token
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()

    def handle_event(self, payload: dict[str, Any]) -> CallbackResult:
        """处理钉钉明文回调事件。"""
        self._verify_token_if_configured(payload)
        encrypted = payload.get("encrypt") or payload.get("encryptMsg")
        if encrypted:
            return CallbackResult(
                platform=self.platform,
                event_type="encrypted_callback",
                payload={"encrypt": encrypted},
                needs_decryption=True,
                response_body=None,
                message="钉钉回调为加密事件，需要开放平台 SDK 解密并生成平台要求的响应后再确认成功。",
            )

        event_type = str(payload.get("EventType") or payload.get("eventType") or payload.get("type") or "dingtalk_callback")
        event_id = self._event_id(payload)
        key = build_idempotency_key(
            provider=self.platform.value,
            event_type=event_type,
            external_event_id=event_id,
            payload=payload,
        )
        check_result = self.idempotency_store.check(key)
        if check_result.duplicated:
            return CallbackResult(
                platform=self.platform,
                event_type=event_type,
                event_id=event_id,
                payload=payload,
                duplicated=True,
                response_body={"success": True},
                message="钉钉重复回调，已按幂等规则忽略。",
            )

        approval_event = self._try_build_approval_event(payload)
        self.idempotency_store.mark_processed(
            key,
            {"event_type": event_type, "event_id": event_id},
        )
        return CallbackResult(
            platform=self.platform,
            event_type=event_type,
            event_id=event_id,
            payload=payload,
            response_body={"success": True},
            approval_event=approval_event,
            message="钉钉回调已标准化。",
        )

    def _verify_token_if_configured(self, payload: dict[str, Any]) -> None:
        if not self.callback_token:
            return
        token = payload.get("token") or payload.get("Token") or payload.get("callbackToken")
        if token != self.callback_token:
            raise IntegrationCallbackVerificationError("钉钉回调 token 校验失败。")

    def _event_id(self, payload: dict[str, Any]) -> str | None:
        value = payload.get("EventId") or payload.get("eventId") or payload.get("msgId") or payload.get("processInstanceId")
        return str(value) if value else None

    def _try_build_approval_event(self, payload: dict[str, Any]) -> ApprovalCallbackEvent | None:
        action = payload.get("action") or payload.get("result") or payload.get("processResult")
        approval_id = payload.get("local_approval_id") or payload.get("approval_id")
        if not action or approval_id is None:
            return None
        normalized_action = self._normalize_action(str(action))
        if normalized_action is None:
            return None
        return ApprovalCallbackEvent(
            platform=self.platform,
            external_approval_id=payload.get("processInstanceId") or payload.get("external_approval_id"),
            local_approval_id=int(approval_id),
            actor_external_user_id=payload.get("staffId") or payload.get("userid") or payload.get("actor_external_user_id"),
            action=normalized_action,
            comment=payload.get("comment") or payload.get("remark"),
            raw_payload=payload,
        )

    def _normalize_action(self, value: str) -> ApprovalCallbackAction | None:
        lowered = value.lower()
        if lowered in {"approve", "agree", "approved", "pass", "同意", "通过"}:
            return ApprovalCallbackAction.APPROVE
        if lowered in {"reject", "rejected", "refuse", "deny", "拒绝", "驳回"}:
            return ApprovalCallbackAction.REJECT
        return None

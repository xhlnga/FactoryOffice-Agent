from typing import Any

from app.integrations.callbacks import CallbackResult
from app.integrations.core.exceptions import IntegrationCallbackVerificationError
from app.integrations.core.idempotency import InMemoryIdempotencyStore, build_idempotency_key
from app.integrations.core.schemas import (
    ApprovalCallbackAction,
    ApprovalCallbackEvent,
    IntegrationPlatform,
)


class FeishuCallbackHandler:
    """飞书回调处理器。

    飞书事件订阅支持 URL Challenge，也支持配置 Encrypt Key 后推送加密事件。
    当前处理器处理明文事件、Challenge、可选 verification token 和幂等；加密事件
    返回 needs_decryption=True，由后续接入解密逻辑。
    """

    platform = IntegrationPlatform.FEISHU

    def __init__(
        self,
        *,
        verification_token: str | None = None,
        idempotency_store: InMemoryIdempotencyStore | None = None,
    ) -> None:
        self.verification_token = verification_token
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()

    def handle_event(self, payload: dict[str, Any]) -> CallbackResult:
        """处理飞书事件订阅回调。"""
        if payload.get("type") == "url_verification":
            self._verify_token_if_configured(payload)
            challenge = str(payload.get("challenge", ""))
            return CallbackResult(
                platform=self.platform,
                event_type="url_verification",
                payload=payload,
                response_body={"challenge": challenge},
                message="飞书 URL Challenge 已通过。",
            )

        if payload.get("encrypt"):
            return CallbackResult(
                platform=self.platform,
                event_type="encrypted_callback",
                payload={"encrypt": payload.get("encrypt")},
                needs_decryption=True,
                response_body=None,
                message="飞书回调为加密事件，需要按 Encrypt Key 解密；若是 URL Challenge，必须解密后返回 challenge。",
            )

        self._verify_token_if_configured(payload)
        header = payload.get("header") if isinstance(payload.get("header"), dict) else {}
        event_type = str(header.get("event_type") or payload.get("type") or "feishu_callback")
        event_id = header.get("event_id") or payload.get("uuid") or payload.get("event_id")
        event_id = str(event_id) if event_id else None
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
                response_body={"code": 0},
                message="飞书重复回调，已按幂等规则忽略。",
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
            response_body={"code": 0},
            approval_event=approval_event,
            message="飞书回调已标准化。",
        )

    def _verify_token_if_configured(self, payload: dict[str, Any]) -> None:
        if not self.verification_token:
            return
        token = payload.get("token") or payload.get("verification_token")
        if token != self.verification_token:
            raise IntegrationCallbackVerificationError("飞书回调 verification token 校验失败。")

    def _try_build_approval_event(self, payload: dict[str, Any]) -> ApprovalCallbackEvent | None:
        event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
        action = event.get("action") or event.get("action_type") or event.get("value")
        approval_id = event.get("local_approval_id") or event.get("approval_id")
        if not action or approval_id is None:
            return None
        normalized_action = self._normalize_action(str(action))
        if normalized_action is None:
            return None
        return ApprovalCallbackEvent(
            platform=self.platform,
            external_approval_id=event.get("approval_code") or event.get("external_approval_id"),
            external_task_id=event.get("open_message_id") or event.get("message_id"),
            local_approval_id=int(approval_id),
            actor_external_user_id=event.get("operator_id") or event.get("open_id") or event.get("user_id"),
            action=normalized_action,
            comment=event.get("comment") or event.get("remark"),
            raw_payload=payload,
        )

    def _normalize_action(self, value: str) -> ApprovalCallbackAction | None:
        lowered = value.lower()
        if lowered in {"approve", "agree", "approved", "confirm", "同意", "通过"}:
            return ApprovalCallbackAction.APPROVE
        if lowered in {"reject", "rejected", "cancel", "refuse", "拒绝", "驳回"}:
            return ApprovalCallbackAction.REJECT
        return None

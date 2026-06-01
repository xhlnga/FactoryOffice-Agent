import hashlib
import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Any

from app.integrations.callbacks import CallbackResult
from app.integrations.core.exceptions import IntegrationCallbackVerificationError
from app.integrations.core.idempotency import InMemoryIdempotencyStore, build_idempotency_key
from app.integrations.core.schemas import IntegrationPlatform


class WeComCallbackHandler:
    """企业微信回调处理器。

    企业微信回调通常涉及 Token、EncodingAESKey、msg_signature、timestamp、nonce。
    当前处理器负责签名校验、URL 验证、XML/字典事件标准化和幂等判断；加密消息
    解密需要后续接入企业微信官方加解密 SDK 或等价实现。
    """

    platform = IntegrationPlatform.WECOM

    def __init__(
        self,
        *,
        token: str,
        decrypt_echo: Callable[[str], str] | None = None,
        idempotency_store: InMemoryIdempotencyStore | None = None,
    ) -> None:
        if not token:
            raise ValueError("企业微信回调 Token 不能为空。")
        self.token = token
        self.decrypt_echo = decrypt_echo
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()

    def verify_signature(
        self,
        *,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        encrypted_payload: str,
    ) -> bool:
        """校验企业微信回调签名。"""
        raw = "".join(sorted([self.token, timestamp, nonce, encrypted_payload]))
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()  # noqa: S324 - 平台协议要求 SHA1
        return digest == msg_signature

    def verify_url(self, query: dict[str, Any]) -> CallbackResult:
        """处理企业微信 URL 验证请求。"""
        echostr = str(query.get("echostr", ""))
        self._ensure_signature_valid(query, encrypted_payload=echostr)
        if self.decrypt_echo is None:
            return CallbackResult(
                platform=self.platform,
                event_type="url_verification",
                payload={"echostr": echostr},
                needs_decryption=True,
                response_body=None,
                message="企业微信 URL 验证签名通过，但 echostr 需要解密后返回；当前未配置解密函数。",
            )
        plain_echo = self.decrypt_echo(echostr)
        return CallbackResult(
            platform=self.platform,
            event_type="url_verification",
            payload={"echostr": echostr},
            needs_decryption=False,
            response_body=plain_echo,
            message="企业微信 URL 验证签名通过，已返回解密后的 echostr。",
        )

    def handle_event(self, *, query: dict[str, Any], body: str | bytes | dict[str, Any]) -> CallbackResult:
        """处理企业微信事件回调。"""
        payload = self._normalize_body(body)
        encrypted_payload = str(payload.get("Encrypt") or payload.get("encrypt") or "")
        if encrypted_payload:
            self._ensure_signature_valid(query, encrypted_payload=encrypted_payload)

        event_type = str(payload.get("Event") or payload.get("MsgType") or "wecom_callback")
        event_id = str(payload.get("MsgId") or payload.get("EventKey") or "") or None
        needs_decryption = bool(encrypted_payload)
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
                needs_decryption=needs_decryption,
                response_body="success",
                message="企业微信重复回调，已按幂等规则忽略。",
            )

        mark_result = self.idempotency_store.mark_processed(
            key,
            {"event_type": event_type, "event_id": event_id},
        )
        return CallbackResult(
            platform=self.platform,
            event_type=event_type,
            event_id=event_id,
            payload=payload,
            duplicated=mark_result.duplicated,
            needs_decryption=needs_decryption,
            response_body="success",
            message="企业微信回调已标准化；加密正文需解密后才能执行业务动作。" if needs_decryption else "企业微信回调已处理。",
        )

    def _ensure_signature_valid(self, query: dict[str, Any], *, encrypted_payload: str) -> None:
        msg_signature = str(query.get("msg_signature") or "")
        timestamp = str(query.get("timestamp") or "")
        nonce = str(query.get("nonce") or "")
        if not all([msg_signature, timestamp, nonce]):
            raise IntegrationCallbackVerificationError(
                "企业微信回调缺少签名参数。",
                details={"required": ["msg_signature", "timestamp", "nonce"]},
            )
        if not self.verify_signature(
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce,
            encrypted_payload=encrypted_payload,
        ):
            raise IntegrationCallbackVerificationError("企业微信回调签名校验失败。")

    def _normalize_body(self, body: str | bytes | dict[str, Any]) -> dict[str, Any]:
        if isinstance(body, dict):
            return body
        text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
        text = text.strip()
        if not text:
            return {}
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return {"raw_body": text}
        return {child.tag: child.text or "" for child in list(root)}

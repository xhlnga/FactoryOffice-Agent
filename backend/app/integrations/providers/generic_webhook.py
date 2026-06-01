import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.integrations.core.base import ApprovalProvider, BusinessSystemProvider, NotificationProvider
from app.integrations.core.exceptions import (
    IntegrationCallbackVerificationError,
    IntegrationConfigError,
)
from app.integrations.core.idempotency import build_business_idempotency_key
from app.integrations.core.schemas import (
    ApprovalCallbackAction,
    ApprovalCallbackEvent,
    ApprovalTaskPayload,
    ApprovalTaskResult,
    BusinessSyncPayload,
    BusinessSyncResult,
    IntegrationCapability,
    IntegrationEventStatus,
    IntegrationPlatform,
    InteractiveCard,
    NotificationDeliveryResult,
    NotificationMessage,
    ProviderHealthCheck,
)


def utc_now() -> datetime:
    """返回带时区的 UTC 时间，避免日志和幂等判断出现时区歧义。"""
    return datetime.now(timezone.utc)


def model_to_payload(value: Any) -> Any:
    """把 Pydantic 模型转换为可 JSON 序列化的对象。"""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


class WebhookTransportMixin:
    """Webhook 传输工具。

    这里使用标准库 urllib，避免为了一个 HTTP POST 增加额外运行依赖。
    """

    default_timeout_seconds = 5.0

    def webhook_health_check(self) -> ProviderHealthCheck:
        """检查 webhook 配置是否存在，不主动向外部系统发探测请求。"""
        webhook_url = self._optional_config_str("webhook_url")
        return ProviderHealthCheck(
            platform=self.platform,
            healthy=bool(webhook_url),
            message="Webhook URL 已配置。" if webhook_url else "Webhook URL 未配置，当前 Provider 不能发送外部请求。",
            checked_at=utc_now(),
            details={"has_webhook_url": bool(webhook_url)},
        )

    def _optional_config_str(self, key: str) -> str | None:
        value = self.context.config.get(key)
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def _required_config_str(self, key: str) -> str:
        value = self._optional_config_str(key)
        if not value:
            raise IntegrationConfigError(
                f"缺少企业集成配置：{key}",
                details={"platform": self.platform.value, "config_key": key},
            )
        return value

    def _webhook_url(self) -> str:
        return self._validate_webhook_url(self._required_config_str("webhook_url"))

    def _resolve_webhook_url(self) -> str:
        """返回最终请求地址。

        平台 provider 可覆盖该方法，例如钉钉需要把 timestamp/sign 拼到 URL 上。
        """
        return self._webhook_url()

    def _build_headers(self, body: bytes) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "FactoryOffice-Agent/enterprise-integration",
        }
        custom_headers = self.context.config.get("headers")
        if isinstance(custom_headers, dict):
            headers.update({str(key): str(value) for key, value in custom_headers.items()})

        signing_secret = (
            self._optional_config_str("signing_secret")
            or self._optional_config_str("sign_secret")
            or self._optional_config_str("secret")
        )
        if signing_secret:
            timestamp = str(int(utc_now().timestamp()))
            raw = f"{timestamp}.".encode("utf-8") + body
            signature = hmac.new(signing_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
            headers["X-FactoryOffice-Timestamp"] = timestamp
            headers["X-FactoryOffice-Signature"] = f"sha256={signature}"
        return headers

    def _post_webhook(self, payload: dict[str, Any]) -> NotificationDeliveryResult:
        """发送 JSON Webhook，并把响应统一转换为通知投递结果。"""
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        request = Request(
            self._resolve_webhook_url(),
            data=body,
            headers=self._build_headers(body),
            method="POST",
        )
        timeout = float(self.context.config.get("timeout_seconds", self.default_timeout_seconds))
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL 来自管理员配置
                response_body = response.read().decode("utf-8", errors="replace")
                response_code = int(response.status)
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            response_code = int(exc.code)
            return NotificationDeliveryResult(
                success=False,
                response_code=response_code,
                response_body=response_body,
                retryable=response_code == 429 or response_code >= 500,
                error_message=f"Webhook 返回异常状态码：{response_code}",
            )
        except (TimeoutError, URLError, OSError) as exc:
            return NotificationDeliveryResult(
                success=False,
                retryable=True,
                error_message=f"Webhook 请求失败：{exc}",
            )

        return NotificationDeliveryResult(
            success=200 <= response_code < 300,
            response_code=response_code,
            response_body=response_body,
            retryable=response_code == 429 or response_code >= 500,
        )

    def _validate_webhook_url(self, webhook_url: str) -> str:
        """校验 webhook URL，避免把本地文件或非 HTTP 协议当成外部回调。"""
        parsed = urlparse(webhook_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise IntegrationConfigError(
                "Webhook URL 必须是 http 或 https 地址。",
                details={"platform": self.platform.value, "webhook_url": webhook_url},
            )
        if parsed.hostname in {"localhost", "127.0.0.1", "::1"} and not self.context.config.get("allow_localhost"):
            raise IntegrationConfigError(
                "生产配置中不允许默认调用 localhost webhook；本地调试请显式设置 allow_localhost=true。",
                details={"platform": self.platform.value, "host": parsed.hostname},
            )
        return webhook_url


class GenericWebhookProvider(WebhookTransportMixin, NotificationProvider, ApprovalProvider, BusinessSystemProvider):
    """通用 Webhook Provider。

    用于连接还没有专属适配器的 OA、低代码平台、企业服务总线或内部系统。
    """

    platform = IntegrationPlatform.GENERIC_WEBHOOK
    capabilities = frozenset(
        {
            IntegrationCapability.NOTIFICATION,
            IntegrationCapability.APPROVAL,
            IntegrationCapability.BUSINESS,
        }
    )

    def health_check(self) -> ProviderHealthCheck:
        return self.webhook_health_check()

    def send_message(self, message: NotificationMessage) -> NotificationDeliveryResult:
        payload = self._build_event_payload("notification.message", model_to_payload(message))
        return self._post_webhook(payload)

    def send_interactive_card(self, card: InteractiveCard) -> NotificationDeliveryResult:
        payload = self._build_event_payload("notification.card", model_to_payload(card))
        return self._post_webhook(payload)

    def create_approval_task(self, payload: ApprovalTaskPayload) -> ApprovalTaskResult:
        delivery = self._post_webhook(
            self._build_event_payload("approval.created", model_to_payload(payload)),
        )
        return ApprovalTaskResult(
            success=delivery.success,
            external_approval_id=f"webhook-approval-{payload.approval_id}" if delivery.success else None,
            message="Webhook 审批任务已投递。" if delivery.success else (delivery.error_message or "Webhook 审批任务投递失败。"),
            metadata={"delivery": model_to_payload(delivery)},
        )

    def parse_callback(self, payload: dict) -> ApprovalCallbackEvent:
        """解析通用审批回调。

        约定字段：local_approval_id、action、actor_external_user_id、comment。
        """
        try:
            action = ApprovalCallbackAction(str(payload["action"]))
        except (KeyError, ValueError) as exc:
            raise IntegrationCallbackVerificationError(
                "通用审批回调缺少合法 action。",
                details={"payload_keys": sorted(payload.keys())},
            ) from exc

        local_approval_id = payload.get("local_approval_id") or payload.get("approval_id")
        return ApprovalCallbackEvent(
            platform=self.platform,
            external_approval_id=payload.get("external_approval_id"),
            external_task_id=payload.get("external_task_id"),
            local_approval_id=int(local_approval_id) if local_approval_id is not None else None,
            actor_external_user_id=payload.get("actor_external_user_id"),
            action=action,
            comment=payload.get("comment"),
            raw_payload=payload,
        )

    def push_business_object(self, payload: BusinessSyncPayload) -> BusinessSyncResult:
        idempotency_key = payload.idempotency_key or build_business_idempotency_key(
            provider=self.platform.value,
            object_type=payload.object_type.value,
            local_id=payload.local_id,
            action="push",
        )
        delivery = self._post_webhook(
            self._build_event_payload(
                "business.push",
                {
                    **model_to_payload(payload),
                    "idempotency_key": idempotency_key,
                },
            ),
        )
        return BusinessSyncResult(
            success=delivery.success,
            external_id=f"{self.platform.value}-{payload.object_type.value}-{payload.local_id}" if delivery.success else None,
            sync_status=IntegrationEventStatus.SUCCESS if delivery.success else IntegrationEventStatus.FAILED,
            retryable=delivery.retryable,
            error_message=delivery.error_message,
            raw_response={"response_code": delivery.response_code, "response_body": delivery.response_body},
        )

    def sync_status(self, object_type: str, external_id: str) -> BusinessSyncResult:
        status_webhook_url = self._optional_config_str("status_webhook_url")
        if not status_webhook_url:
            return BusinessSyncResult(
                success=False,
                sync_status=IntegrationEventStatus.FAILED,
                error_message="未配置 status_webhook_url，无法从外部系统同步状态。",
            )

        original_url = self.context.config.get("webhook_url")
        self.context.config["webhook_url"] = status_webhook_url
        try:
            delivery = self._post_webhook(
                self._build_event_payload(
                    "business.status_sync",
                    {"object_type": object_type, "external_id": external_id},
                )
            )
        finally:
            self.context.config["webhook_url"] = original_url

        return BusinessSyncResult(
            success=delivery.success,
            external_id=external_id,
            sync_status=IntegrationEventStatus.SUCCESS if delivery.success else IntegrationEventStatus.FAILED,
            retryable=delivery.retryable,
            error_message=delivery.error_message,
            raw_response={"response_code": delivery.response_code, "response_body": delivery.response_body},
        )

    def _build_event_payload(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "event_type": event_type,
            "provider": self.platform.value,
            "enterprise_id": self.enterprise_id,
            "request_id": self.context.request_id,
            "created_at": utc_now().isoformat(),
            "payload": payload,
        }


class GenericBusinessWebhookProvider(WebhookTransportMixin, BusinessSystemProvider):
    """通用业务系统 Webhook Provider 基类。"""

    external_system_name = "BUSINESS"

    def health_check(self) -> ProviderHealthCheck:
        return self.webhook_health_check()

    def push_business_object(self, payload: BusinessSyncPayload) -> BusinessSyncResult:
        delivery = self._post_webhook(
            {
                "event_type": "business.push",
                "provider": self.platform.value,
                "enterprise_id": self.enterprise_id,
                "created_at": utc_now().isoformat(),
                "payload": model_to_payload(payload),
            }
        )
        return BusinessSyncResult(
            success=delivery.success,
            external_id=f"{self.external_system_name}-{payload.object_type.value}-{payload.local_id}" if delivery.success else None,
            sync_status=IntegrationEventStatus.SUCCESS if delivery.success else IntegrationEventStatus.FAILED,
            retryable=delivery.retryable,
            error_message=delivery.error_message,
            raw_response={"response_code": delivery.response_code, "response_body": delivery.response_body},
        )

    def sync_status(self, object_type: str, external_id: str) -> BusinessSyncResult:
        status_webhook_url = self._optional_config_str("status_webhook_url")
        if not status_webhook_url:
            return BusinessSyncResult(
                success=False,
                external_id=external_id,
                sync_status=IntegrationEventStatus.FAILED,
                error_message="未配置 status_webhook_url，当前只能单向推送业务对象。",
            )
        original_url = self.context.config.get("webhook_url")
        self.context.config["webhook_url"] = status_webhook_url
        try:
            delivery = self._post_webhook(
                {
                    "event_type": "business.status_sync",
                    "provider": self.platform.value,
                    "enterprise_id": self.enterprise_id,
                    "created_at": utc_now().isoformat(),
                    "payload": {"object_type": object_type, "external_id": external_id},
                }
            )
        finally:
            self.context.config["webhook_url"] = original_url

        return BusinessSyncResult(
            success=delivery.success,
            external_id=external_id,
            sync_status=IntegrationEventStatus.SUCCESS if delivery.success else IntegrationEventStatus.FAILED,
            retryable=delivery.retryable,
            error_message=delivery.error_message,
            raw_response={"response_code": delivery.response_code, "response_body": delivery.response_body},
        )

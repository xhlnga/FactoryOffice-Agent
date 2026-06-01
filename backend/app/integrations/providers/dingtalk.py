import base64
import hashlib
import hmac
import time
from urllib.parse import quote_plus

from app.integrations.core.base import NotificationProvider
from app.integrations.core.schemas import (
    IntegrationPlatform,
    InteractiveCard,
    NotificationDeliveryResult,
    NotificationMessage,
    ProviderHealthCheck,
)
from app.integrations.providers.generic_webhook import WebhookTransportMixin


class DingTalkProvider(WebhookTransportMixin, NotificationProvider):
    """钉钉 Provider。

    当前实现群自定义机器人通知。钉钉群自定义机器人只适合通知，不适合承载完整
    审批回调；正式审批应接钉钉应用/审批 API。
    """

    platform = IntegrationPlatform.DINGTALK

    def health_check(self) -> ProviderHealthCheck:
        return self.webhook_health_check()

    def send_message(self, message: NotificationMessage) -> NotificationDeliveryResult:
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": message.title,
                "text": self._markdown_message(message.title, message.content, message.action_url),
            },
        }
        return self._post_webhook(payload)

    def send_interactive_card(self, card: InteractiveCard) -> NotificationDeliveryResult:
        lines = [f"### {card.title}", "", card.summary]
        for key, value in card.fields.items():
            lines.append(f"- **{key}**：{value}")
        for action in card.actions:
            if action.action_url:
                lines.append(f"[{action.label}]({action.action_url})")
        payload = {"msgtype": "markdown", "markdown": {"title": card.title, "text": "\n".join(lines)}}
        return self._post_webhook(payload)

    def _resolve_webhook_url(self) -> str:
        webhook_url = self._webhook_url()
        secret = self._optional_config_str("sign_secret") or self._optional_config_str("secret")
        if not secret:
            return webhook_url
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
        sign = quote_plus(base64.b64encode(digest).decode("utf-8"))
        separator = "&" if "?" in webhook_url else "?"
        return f"{webhook_url}{separator}timestamp={timestamp}&sign={sign}"

    def _markdown_message(self, title: str, content: str, action_url: str | None = None) -> str:
        lines = [f"### {title}", "", content]
        if action_url:
            lines.append(f"[查看详情]({action_url})")
        return "\n".join(lines)

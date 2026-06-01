import base64
import hashlib
import hmac
import time

from app.integrations.core.base import NotificationProvider
from app.integrations.core.schemas import (
    IntegrationPlatform,
    InteractiveCard,
    NotificationDeliveryResult,
    NotificationMessage,
    ProviderHealthCheck,
)
from app.integrations.providers.generic_webhook import WebhookTransportMixin


class FeishuProvider(WebhookTransportMixin, NotificationProvider):
    """飞书 Provider。

    当前实现自定义机器人通知。飞书事件订阅和应用身份体系后续应通过独立回调
    服务接入，避免把通知机器人误当成完整业务应用。
    """

    platform = IntegrationPlatform.FEISHU

    def health_check(self) -> ProviderHealthCheck:
        return self.webhook_health_check()

    def send_message(self, message: NotificationMessage) -> NotificationDeliveryResult:
        payload = {
            "msg_type": "text",
            "content": {"text": self._plain_text_message(message.title, message.content, message.action_url)},
        }
        payload.update(self._signature_payload())
        return self._post_webhook(payload)

    def send_interactive_card(self, card: InteractiveCard) -> NotificationDeliveryResult:
        elements: list[dict] = [
            {"tag": "div", "text": {"tag": "lark_md", "content": card.summary}},
        ]
        if card.fields:
            field_text = "\n".join(f"**{key}**：{value}" for key, value in card.fields.items())
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": field_text}})
        for action in card.actions:
            if action.action_url:
                elements.append(
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": action.label},
                                "url": action.action_url,
                                "type": "primary",
                            }
                        ],
                    }
                )
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {"title": {"tag": "plain_text", "content": card.title}},
                "elements": elements,
            },
        }
        payload.update(self._signature_payload())
        return self._post_webhook(payload)

    def _signature_payload(self) -> dict[str, str]:
        secret = self._optional_config_str("sign_secret") or self._optional_config_str("secret")
        if not secret:
            return {}
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(string_to_sign.encode("utf-8"), b"", hashlib.sha256).digest()
        return {
            "timestamp": timestamp,
            "sign": base64.b64encode(digest).decode("utf-8"),
        }

    def _plain_text_message(self, title: str, content: str, action_url: str | None = None) -> str:
        lines = [f"【{title}】", content]
        if action_url:
            lines.append(f"查看详情：{action_url}")
        return "\n".join(lines)

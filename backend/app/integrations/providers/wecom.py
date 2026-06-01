from app.integrations.core.base import NotificationProvider
from app.integrations.core.schemas import (
    IntegrationPlatform,
    InteractiveCard,
    NotificationDeliveryResult,
    NotificationMessage,
    ProviderHealthCheck,
)
from app.integrations.providers.generic_webhook import WebhookTransportMixin


class WeComProvider(WebhookTransportMixin, NotificationProvider):
    """企业微信 Provider。

    当前实现企业微信群机器人通知。完整 OAuth、通讯录同步和回调解密需要企业应用
    的 CorpId、Secret、Token、EncodingAESKey，应通过企业集成配置、SSO 服务和回调
    服务按客户实际开放平台权限接入。
    """

    platform = IntegrationPlatform.WECOM

    def health_check(self) -> ProviderHealthCheck:
        return self.webhook_health_check()

    def send_message(self, message: NotificationMessage) -> NotificationDeliveryResult:
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": self._markdown_message(message.title, message.content, message.action_url)},
        }
        return self._post_webhook(payload)

    def send_interactive_card(self, card: InteractiveCard) -> NotificationDeliveryResult:
        content = [f"**{card.title}**", "", card.summary]
        for key, value in card.fields.items():
            content.append(f"> {key}：{value}")
        for action in card.actions:
            if action.action_url:
                content.append(f"[{action.label}]({action.action_url})")
        return self._post_webhook({"msgtype": "markdown", "markdown": {"content": "\n".join(content)}})

    def _markdown_message(self, title: str, content: str, action_url: str | None = None) -> str:
        parts = [f"**{title}**", "", content]
        if action_url:
            parts.append(f"[查看详情]({action_url})")
        return "\n".join(parts)

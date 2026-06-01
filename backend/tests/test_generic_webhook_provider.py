import pytest

from app.integrations.core.exceptions import IntegrationConfigError
from app.integrations.core.schemas import IntegrationPlatform, NotificationMessage, ProviderContext
from app.integrations.providers.generic_webhook import GenericWebhookProvider


def test_generic_webhook_rejects_missing_url() -> None:
    """通用 Webhook 没有 URL 时不能静默成功。"""
    provider = GenericWebhookProvider(ProviderContext(platform=IntegrationPlatform.GENERIC_WEBHOOK))

    with pytest.raises(IntegrationConfigError):
        provider.send_message(NotificationMessage(title="测试", content="缺少 URL"))


def test_generic_webhook_rejects_non_http_url() -> None:
    """Webhook 只能使用 HTTP/HTTPS，不能把本地文件路径当接口。"""
    provider = GenericWebhookProvider(
        ProviderContext(platform=IntegrationPlatform.GENERIC_WEBHOOK, config={"webhook_url": "file:///tmp/a"})
    )

    with pytest.raises(IntegrationConfigError):
        provider.send_message(NotificationMessage(title="测试", content="非法协议"))


def test_generic_webhook_rejects_localhost_unless_explicitly_allowed() -> None:
    """生产默认不允许调用 localhost，避免 SSRF 和误配。"""
    provider = GenericWebhookProvider(
        ProviderContext(platform=IntegrationPlatform.GENERIC_WEBHOOK, config={"webhook_url": "http://localhost:8000"})
    )

    with pytest.raises(IntegrationConfigError):
        provider.send_message(NotificationMessage(title="测试", content="localhost"))


def test_generic_webhook_accepts_frontend_sign_secret_alias() -> None:
    """前端使用 sign_secret 字段，通用 Webhook 也应能生成签名头。"""
    provider = GenericWebhookProvider(
        ProviderContext(
            platform=IntegrationPlatform.GENERIC_WEBHOOK,
            config={"webhook_url": "https://example.com/hook", "sign_secret": "demo-secret"},
        )
    )

    headers = provider._build_headers(b'{"ok":true}')  # noqa: SLF001 - 这里专门验证签名兼容字段

    assert "X-FactoryOffice-Timestamp" in headers
    assert headers["X-FactoryOffice-Signature"].startswith("sha256=")

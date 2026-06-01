from app.integrations.core.registry import register_provider
from app.integrations.core.schemas import IntegrationPlatform
from app.integrations.providers.dingtalk import DingTalkProvider
from app.integrations.providers.feishu import FeishuProvider
from app.integrations.providers.generic_erp import GenericERPProvider
from app.integrations.providers.generic_mes import GenericMESProvider
from app.integrations.providers.generic_oa import GenericOAProvider
from app.integrations.providers.generic_webhook import GenericWebhookProvider
from app.integrations.providers.generic_wms import GenericWMSProvider
from app.integrations.providers.local import LocalIntegrationProvider
from app.integrations.providers.wecom import WeComProvider


def register_builtin_providers(*, replace: bool = False) -> None:
    """注册项目内置的企业集成 Provider。"""
    register_provider(IntegrationPlatform.LOCAL, LocalIntegrationProvider, replace=replace)
    register_provider(IntegrationPlatform.GENERIC_WEBHOOK, GenericWebhookProvider, replace=replace)
    register_provider(IntegrationPlatform.WECOM, WeComProvider, replace=replace)
    register_provider(IntegrationPlatform.DINGTALK, DingTalkProvider, replace=replace)
    register_provider(IntegrationPlatform.FEISHU, FeishuProvider, replace=replace)
    register_provider(IntegrationPlatform.GENERIC_OA, GenericOAProvider, replace=replace)
    register_provider(IntegrationPlatform.GENERIC_ERP, GenericERPProvider, replace=replace)
    register_provider(IntegrationPlatform.GENERIC_MES, GenericMESProvider, replace=replace)
    register_provider(IntegrationPlatform.GENERIC_WMS, GenericWMSProvider, replace=replace)


__all__ = [
    "DingTalkProvider",
    "FeishuProvider",
    "GenericERPProvider",
    "GenericMESProvider",
    "GenericOAProvider",
    "GenericWMSProvider",
    "GenericWebhookProvider",
    "LocalIntegrationProvider",
    "WeComProvider",
    "register_builtin_providers",
]

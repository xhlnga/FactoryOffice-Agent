from collections.abc import Callable

from app.integrations.core.base import BaseIntegrationProvider
from app.integrations.core.exceptions import IntegrationProviderNotFoundError
from app.integrations.core.schemas import IntegrationPlatform, ProviderContext


ProviderFactory = Callable[[ProviderContext], BaseIntegrationProvider]


class IntegrationProviderRegistry:
    """企业集成 Provider 注册表。

    各平台 provider 在应用启动或模块导入时注册。业务代码通过 platform 获取
    provider，不需要知道具体类名。
    """

    def __init__(self) -> None:
        self._factories: dict[IntegrationPlatform, ProviderFactory] = {}

    def register(self, platform: IntegrationPlatform, factory: ProviderFactory, *, replace: bool = False) -> None:
        """注册 provider 工厂。"""
        if platform in self._factories and not replace:
            raise ValueError(f"Provider 已注册：{platform.value}")
        self._factories[platform] = factory

    def unregister(self, platform: IntegrationPlatform) -> None:
        """取消注册 provider。"""
        self._factories.pop(platform, None)

    def get(self, platform: IntegrationPlatform, context: ProviderContext) -> BaseIntegrationProvider:
        """根据平台获取 provider 实例。"""
        factory = self._factories.get(platform)
        if factory is None:
            raise IntegrationProviderNotFoundError(platform.value)
        return factory(context)

    def has(self, platform: IntegrationPlatform) -> bool:
        """判断平台是否已注册。"""
        return platform in self._factories

    def registered_platforms(self) -> list[IntegrationPlatform]:
        """返回已注册平台列表。"""
        return sorted(self._factories.keys(), key=lambda item: item.value)

    def clear(self) -> None:
        """清空注册表，主要用于测试。"""
        self._factories.clear()


provider_registry = IntegrationProviderRegistry()


def register_provider(platform: IntegrationPlatform, factory: ProviderFactory, *, replace: bool = False) -> None:
    """注册 provider 的便捷函数。"""
    provider_registry.register(platform, factory, replace=replace)


def get_provider(platform: IntegrationPlatform, context: ProviderContext) -> BaseIntegrationProvider:
    """获取 provider 的便捷函数。"""
    return provider_registry.get(platform, context)


from app.integrations.core.base import BaseIntegrationProvider, IdentityProvider
from app.integrations.core.registry import IntegrationProviderRegistry, provider_registry
from app.integrations.core.schemas import (
    ExternalUserProfile,
    IdentityAuthCode,
    IntegrationCapability,
    IntegrationPlatform,
    ProviderContext,
)
from app.integrations.providers import register_builtin_providers


class SSOService:
    """企业登录服务。

    这一层只负责把企业平台身份换成本系统可理解的用户信息。真正签发 JWT、绑定
    本地用户、离职冻结，需要接入账号模型后再做。
    """

    def __init__(self, registry: IntegrationProviderRegistry | None = None) -> None:
        if registry is None:
            register_builtin_providers(replace=True)
        self.registry = registry or provider_registry

    def exchange_code(
        self,
        *,
        platform: IntegrationPlatform,
        code: str,
        config: dict | None = None,
        enterprise_id: int | None = None,
        redirect_uri: str | None = None,
        state: str | None = None,
    ) -> ExternalUserProfile:
        """用企业授权码换取外部用户信息。"""
        provider = self._identity_provider(platform, config=config, enterprise_id=enterprise_id)
        return provider.exchange_code_for_user(IdentityAuthCode(code=code, redirect_uri=redirect_uri, state=state))

    def get_user_profile(
        self,
        *,
        platform: IntegrationPlatform,
        external_user_id: str,
        config: dict | None = None,
        enterprise_id: int | None = None,
    ) -> ExternalUserProfile:
        """按外部用户 ID 查询用户信息。"""
        provider = self._identity_provider(platform, config=config, enterprise_id=enterprise_id)
        return provider.get_user_profile(external_user_id)

    def build_session_claims(self, profile: ExternalUserProfile, *, default_role: str = "employee") -> dict:
        """构造本地会话声明。

        注意：这里不签发 token，只返回后续认证模块可使用的声明字段。
        """
        return {
            "external_user_id": profile.external_user_id,
            "name": profile.name,
            "enterprise_id": profile.enterprise_id,
            "external_department_ids": profile.external_department_ids,
            "position": profile.position,
            "active": profile.active,
            "role": default_role,
        }

    def _identity_provider(
        self,
        platform: IntegrationPlatform,
        *,
        config: dict | None,
        enterprise_id: int | None,
    ) -> IdentityProvider:
        provider: BaseIntegrationProvider = self.registry.get(
            platform,
            ProviderContext(platform=platform, enterprise_id=enterprise_id, config=config or {}),
        )
        provider.ensure_capability(IntegrationCapability.IDENTITY)
        return provider  # type: ignore[return-value]

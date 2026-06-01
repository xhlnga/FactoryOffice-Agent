"""企业集成核心抽象。"""

from app.integrations.core.base import (
    ApprovalProvider,
    BaseIntegrationProvider,
    BusinessSystemProvider,
    IdentityProvider,
    NotificationProvider,
    OrgProvider,
)
from app.integrations.core.schemas import IntegrationCapability, IntegrationPlatform

__all__ = [
    "ApprovalProvider",
    "BaseIntegrationProvider",
    "BusinessSystemProvider",
    "IdentityProvider",
    "IntegrationCapability",
    "IntegrationPlatform",
    "NotificationProvider",
    "OrgProvider",
]


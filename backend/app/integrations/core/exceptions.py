from typing import Any

from fastapi import status

from app.core.exceptions import AppException


class IntegrationError(AppException):
    """企业集成层基础异常。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        error_code: str = "INTEGRATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            details=details,
        )


class IntegrationConfigError(IntegrationError):
    """企业集成配置缺失或不合法。"""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INTEGRATION_CONFIG_ERROR",
            details=details,
        )


class IntegrationProviderNotFoundError(IntegrationError):
    """未找到指定平台的 Provider。"""

    def __init__(self, platform: str) -> None:
        super().__init__(
            "未找到对应的企业集成 Provider。",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="INTEGRATION_PROVIDER_NOT_FOUND",
            details={"platform": platform},
        )


class IntegrationCapabilityError(IntegrationError):
    """Provider 不支持当前能力。"""

    def __init__(self, platform: str, capability: str) -> None:
        super().__init__(
            "当前企业集成 Provider 不支持该能力。",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INTEGRATION_CAPABILITY_UNSUPPORTED",
            details={"platform": platform, "capability": capability},
        )


class IntegrationAuthError(IntegrationError):
    """外部平台鉴权失败。"""

    def __init__(self, message: str = "外部平台鉴权失败。", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INTEGRATION_AUTH_ERROR",
            details=details,
        )


class IntegrationCallbackVerificationError(IntegrationError):
    """外部平台回调验签或解密失败。"""

    def __init__(self, message: str = "外部平台回调校验失败。", *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INTEGRATION_CALLBACK_VERIFY_FAILED",
            details=details,
        )


class IntegrationRetryableError(IntegrationError):
    """可重试的外部系统错误，例如超时、限流、临时不可用。"""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="INTEGRATION_RETRYABLE_ERROR",
            details=details,
        )


class IntegrationNotImplementedError(IntegrationError):
    """Provider 还没有实现某个具体动作。"""

    def __init__(self, platform: str, method_name: str) -> None:
        super().__init__(
            "当前企业集成 Provider 尚未实现该动作。",
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            error_code="INTEGRATION_NOT_IMPLEMENTED",
            details={"platform": platform, "method_name": method_name},
        )


from app.integrations.core.base import BaseIntegrationProvider, NotificationProvider
from app.integrations.core.exceptions import IntegrationError, IntegrationRetryableError
from app.integrations.core.registry import IntegrationProviderRegistry, provider_registry
from app.integrations.core.schemas import (
    IntegrationCapability,
    IntegrationPlatform,
    InteractiveCard,
    InteractiveCardAction,
    NotificationDeliveryResult,
    NotificationMessage,
    NotificationRecipient,
    NotificationSeverity,
    ProviderContext,
)
from app.integrations.providers import register_builtin_providers
from app.models.base import NotificationDeliveryStatus
from app.models.notification_delivery import NotificationDelivery
from app.utils.time_utils import utc_now


class NotificationService:
    """统一通知服务。

    业务代码只调用这一层，不直接调用企业微信、钉钉或飞书 Provider。
    """

    def __init__(self, registry: IntegrationProviderRegistry | None = None) -> None:
        if registry is None:
            register_builtin_providers(replace=True)
        self.registry = registry or provider_registry

    def send_message(
        self,
        *,
        platform: IntegrationPlatform,
        title: str,
        content: str,
        db=None,
        config: dict | None = None,
        enterprise_id: int | None = None,
        recipients: list[NotificationRecipient] | None = None,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        business_type: str | None = None,
        business_id: int | str | None = None,
        action_url: str | None = None,
        request_id: str | None = None,
        metadata: dict | None = None,
        commit: bool = True,
    ) -> NotificationDeliveryResult:
        """发送普通通知。"""
        message = NotificationMessage(
            title=title,
            content=content,
            recipients=recipients or [],
            severity=severity,
            business_type=business_type,
            business_id=business_id,
            action_url=action_url,
            metadata=metadata or {},
        )
        delivery = self._create_delivery(
            db,
            platform=platform,
            enterprise_id=enterprise_id,
            message_type="message",
            title=title,
            action_url=action_url,
            payload_snapshot={
                "title": title,
                "content": content,
                "severity": severity.value,
                "action_url": action_url,
                "metadata": metadata or {},
            },
            recipients=message.recipients,
            business_type=business_type,
            business_id=business_id,
        )
        try:
            provider = self._notification_provider(platform, config=config, enterprise_id=enterprise_id, request_id=request_id)
            result = provider.send_message(message)
        except Exception as exc:  # noqa: BLE001 - 企业集成异常需要落库，避免通知记录长期 pending
            result = self._result_from_exception(exc)
        self._finish_delivery(db, delivery, result, commit=commit)
        return result

    def send_card(
        self,
        *,
        platform: IntegrationPlatform,
        title: str,
        summary: str,
        db=None,
        config: dict | None = None,
        enterprise_id: int | None = None,
        fields: dict | None = None,
        recipients: list[NotificationRecipient] | None = None,
        actions: list[InteractiveCardAction] | None = None,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        business_type: str | None = None,
        business_id: int | str | None = None,
        request_id: str | None = None,
        metadata: dict | None = None,
        commit: bool = True,
    ) -> NotificationDeliveryResult:
        """发送结构化卡片通知。"""
        card = InteractiveCard(
            title=title,
            summary=summary,
            fields=fields or {},
            recipients=recipients or [],
            actions=actions or [],
            severity=severity,
            business_type=business_type,
            business_id=business_id,
            metadata=metadata or {},
        )
        delivery = self._create_delivery(
            db,
            platform=platform,
            enterprise_id=enterprise_id,
            message_type="interactive_card",
            title=title,
            action_url=_first_action_url(actions or []),
            payload_snapshot={
                "title": title,
                "summary": summary,
                "fields": fields or {},
                "actions": [action.model_dump() for action in actions or []],
                "severity": severity.value,
                "metadata": metadata or {},
            },
            recipients=card.recipients,
            business_type=business_type,
            business_id=business_id,
        )
        try:
            provider = self._notification_provider(platform, config=config, enterprise_id=enterprise_id, request_id=request_id)
            result = provider.send_interactive_card(card)
        except Exception as exc:  # noqa: BLE001 - 企业集成异常需要落库，避免通知记录长期 pending
            result = self._result_from_exception(exc)
        self._finish_delivery(db, delivery, result, commit=commit)
        return result

    def notify_approval_created(
        self,
        *,
        platform: IntegrationPlatform,
        approval_id: int,
        title: str,
        summary: str,
        db=None,
        config: dict | None = None,
        enterprise_id: int | None = None,
        action_url: str | None = None,
        recipients: list[NotificationRecipient] | None = None,
        commit: bool = True,
    ) -> NotificationDeliveryResult:
        """发送审批待办通知。"""
        actions = [
            InteractiveCardAction(key="view", label="查看详情", action_url=action_url),
        ] if action_url else []
        return self.send_card(
            platform=platform,
            title=title,
            summary=summary,
            db=db,
            config=config,
            enterprise_id=enterprise_id,
            fields={"审批编号": approval_id, "状态": "待审批"},
            recipients=recipients,
            actions=actions,
            severity=NotificationSeverity.WARNING,
            business_type="approval",
            business_id=approval_id,
            commit=commit,
        )

    def _notification_provider(
        self,
        platform: IntegrationPlatform,
        *,
        config: dict | None,
        enterprise_id: int | None,
        request_id: str | None,
    ) -> NotificationProvider:
        provider = self._provider(platform, config=config, enterprise_id=enterprise_id, request_id=request_id)
        provider.ensure_capability(IntegrationCapability.NOTIFICATION)
        return provider  # type: ignore[return-value]

    def _provider(
        self,
        platform: IntegrationPlatform,
        *,
        config: dict | None,
        enterprise_id: int | None,
        request_id: str | None,
    ) -> BaseIntegrationProvider:
        return self.registry.get(
            platform,
            ProviderContext(
                platform=platform,
                enterprise_id=enterprise_id,
                config=config or {},
                request_id=request_id,
            ),
        )

    def _create_delivery(
        self,
        db,
        *,
        platform: IntegrationPlatform,
        enterprise_id: int | None,
        message_type: str,
        title: str,
        action_url: str | None,
        payload_snapshot: dict | None,
        recipients: list[NotificationRecipient],
        business_type: str | None,
        business_id: int | str | None,
    ) -> NotificationDelivery | None:
        """创建通知投递记录；测试替身或无数据库时跳过。"""
        if db is None or not all(hasattr(db, attr) for attr in ("add", "flush")):
            return None

        first_recipient = recipients[0] if recipients else None
        delivery = NotificationDelivery(
            enterprise_id=enterprise_id,
            platform=platform.value,
            recipient_user_id=first_recipient.user_id if first_recipient else None,
            recipient_external_user_id=first_recipient.external_user_id if first_recipient else None,
            message_type=message_type,
            title=title,
            action_url=action_url,
            payload_snapshot=payload_snapshot,
            business_type=business_type,
            business_id=str(business_id) if business_id is not None else None,
            status=NotificationDeliveryStatus.PENDING,
        )
        db.add(delivery)
        db.flush()
        return delivery

    def _finish_delivery(
        self,
        db,
        delivery: NotificationDelivery | None,
        result: NotificationDeliveryResult,
        *,
        commit: bool,
    ) -> None:
        """更新通知投递结果。"""
        if delivery is None:
            return

        delivery.status = (
            NotificationDeliveryStatus.SUCCESS
            if result.success
            else NotificationDeliveryStatus.RETRYING
            if result.retryable
            else NotificationDeliveryStatus.FAILED
        )
        delivery.response_code = result.response_code
        delivery.response_body = result.response_body
        delivery.retryable = result.retryable
        delivery.last_error = result.error_message
        delivery.delivered_at = utc_now() if result.success else None
        result.metadata["delivery_id"] = delivery.id
        if result.retryable and not result.success:
            delivery.retry_count += 1

        if commit and db is not None and hasattr(db, "commit"):
            db.commit()

    def _result_from_exception(self, exc: Exception) -> NotificationDeliveryResult:
        """把 Provider 异常转换成可落库、可重试判断的投递结果。"""
        retryable = isinstance(exc, IntegrationRetryableError) or not isinstance(exc, IntegrationError)
        return NotificationDeliveryResult(
            success=False,
            retryable=retryable,
            error_message=str(exc),
            metadata={"exception_type": exc.__class__.__name__},
        )


def _first_action_url(actions: list[InteractiveCardAction]) -> str | None:
    """提取卡片第一条跳转链接，用于失败重试。"""
    for action in actions:
        if action.action_url:
            return action.action_url
    return None

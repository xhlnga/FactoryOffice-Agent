from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.integrations.core.schemas import (
    IntegrationPlatform,
    NotificationDeliveryResult,
    NotificationRecipient,
    NotificationSeverity,
)
from app.integrations.providers.generic_webhook import utc_now
from app.integrations.services.notification_service import NotificationService


class SLAStatus(StrEnum):
    """SLA 状态。"""

    NORMAL = "normal"
    REMINDING = "reminding"
    BREACHED = "breached"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class SLAPolicy:
    """SLA 策略。"""

    business_type: str
    priority: str
    response_minutes: int
    resolve_minutes: int
    remind_before_minutes: int
    escalate_after_minutes: int
    escalate_to_role: str


@dataclass(frozen=True)
class SLAEvaluation:
    """SLA 评估结果。"""

    status: SLAStatus
    response_due_at: datetime
    deadline_at: datetime
    remind_at: datetime
    escalate_at: datetime
    minutes_left: int
    message: str
    policy: SLAPolicy


class SLAEscalationService:
    """SLA 提醒和升级服务。

    当前提供可被定时任务调用的评估和通知能力。实际落库由 sla_instances、
    notification_deliveries 和 integration_events 相关 job/service 完成，本类保留为
    纯规则计算和通知内容构造入口，避免把业务判断散落到多个定时任务里。
    """

    DEFAULT_POLICIES: dict[tuple[str, str], SLAPolicy] = {
        ("ticket", "urgent"): SLAPolicy("ticket", "urgent", 15, 120, 30, 60, "equipment_manager"),
        ("ticket", "high"): SLAPolicy("ticket", "high", 30, 240, 60, 120, "equipment_manager"),
        ("ticket", "medium"): SLAPolicy("ticket", "medium", 120, 1440, 120, 240, "department_manager"),
        ("ticket", "low"): SLAPolicy("ticket", "low", 1440, 4320, 240, 480, "department_manager"),
        ("quality_issue", "urgent"): SLAPolicy("quality_issue", "urgent", 30, 480, 60, 120, "quality_manager"),
        ("quality_issue", "high"): SLAPolicy("quality_issue", "high", 60, 720, 120, 240, "quality_manager"),
        ("purchase_request", "urgent"): SLAPolicy("purchase_request", "urgent", 240, 1440, 240, 480, "purchase_manager"),
        ("purchase_request", "medium"): SLAPolicy("purchase_request", "medium", 480, 2880, 480, 960, "purchase_manager"),
    }

    def __init__(self, notification_service: NotificationService | None = None) -> None:
        self.notification_service = notification_service or NotificationService()

    def get_policy(self, *, business_type: str, priority: str) -> SLAPolicy:
        """获取 SLA 策略，找不到时回落到中等优先级。"""
        return (
            self.DEFAULT_POLICIES.get((business_type, priority))
            or self.DEFAULT_POLICIES.get((business_type, "medium"))
            or SLAPolicy(business_type, priority, 240, 1440, 240, 480, "department_manager")
        )

    def evaluate(
        self,
        *,
        business_type: str,
        priority: str,
        created_at: datetime,
        resolved_at: datetime | None = None,
        now: datetime | None = None,
    ) -> SLAEvaluation:
        """评估业务对象当前 SLA 状态。"""
        policy = self.get_policy(business_type=business_type, priority=priority)
        current_time = now or utc_now()
        response_due_at = created_at + timedelta(minutes=policy.response_minutes)
        deadline_at = created_at + timedelta(minutes=policy.resolve_minutes)
        remind_at = deadline_at - timedelta(minutes=policy.remind_before_minutes)
        escalate_at = deadline_at + timedelta(minutes=policy.escalate_after_minutes)

        if resolved_at is not None:
            status = SLAStatus.RESOLVED
            message = "业务对象已完成，SLA 已关闭。"
        elif current_time >= escalate_at:
            status = SLAStatus.ESCALATED
            message = "业务对象已严重超出 SLA，建议升级给上级负责人。"
        elif current_time >= deadline_at:
            status = SLAStatus.BREACHED
            message = "业务对象已超出 SLA。"
        elif current_time >= response_due_at:
            status = SLAStatus.REMINDING
            message = "业务对象已超过响应时限，请尽快确认处理。"
        elif current_time >= remind_at:
            status = SLAStatus.REMINDING
            message = "业务对象即将超出 SLA，请及时处理。"
        else:
            status = SLAStatus.NORMAL
            message = "业务对象仍在 SLA 时间内。"

        minutes_left = int((deadline_at - current_time).total_seconds() // 60)
        return SLAEvaluation(
            status=status,
            response_due_at=response_due_at,
            deadline_at=deadline_at,
            remind_at=remind_at,
            escalate_at=escalate_at,
            minutes_left=minutes_left,
            message=message,
            policy=policy,
        )

    def notify_if_needed(
        self,
        *,
        platform: IntegrationPlatform,
        business_type: str,
        business_id: int | str,
        title: str,
        priority: str,
        created_at: datetime,
        config: dict | None = None,
        enterprise_id: int | None = None,
        resolved_at: datetime | None = None,
        now: datetime | None = None,
        recipients: list[NotificationRecipient] | None = None,
        action_url: str | None = None,
    ) -> NotificationDeliveryResult | None:
        """需要提醒或升级时发送 SLA 通知。"""
        evaluation = self.evaluate(
            business_type=business_type,
            priority=priority,
            created_at=created_at,
            resolved_at=resolved_at,
            now=now,
        )
        if evaluation.status in {SLAStatus.NORMAL, SLAStatus.RESOLVED}:
            return None

        severity = NotificationSeverity.URGENT if evaluation.status == SLAStatus.ESCALATED else NotificationSeverity.WARNING
        return self.notification_service.send_message(
            platform=platform,
            title=f"SLA 提醒：{title}",
            content=(
                f"{evaluation.message}\n"
                f"业务类型：{business_type}\n"
                f"业务编号：{business_id}\n"
                f"优先级：{priority}\n"
                f"SLA 响应时限：{evaluation.response_due_at.isoformat()}\n"
                f"SLA 截止时间：{evaluation.deadline_at.isoformat()}\n"
                f"建议升级角色：{evaluation.policy.escalate_to_role}"
            ),
            config=config,
            enterprise_id=enterprise_id,
            recipients=recipients,
            severity=severity,
            business_type=business_type,
            business_id=business_id,
            action_url=action_url,
        )

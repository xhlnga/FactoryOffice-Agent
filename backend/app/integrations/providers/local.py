from app.integrations.core.base import (
    ApprovalProvider,
    BusinessSystemProvider,
    IdentityProvider,
    NotificationProvider,
    OrgProvider,
)
from app.integrations.core.exceptions import IntegrationCallbackVerificationError
from app.integrations.core.schemas import (
    ApprovalCallbackAction,
    ApprovalCallbackEvent,
    ApprovalTaskPayload,
    ApprovalTaskResult,
    BusinessSyncPayload,
    BusinessSyncResult,
    DepartmentRecord,
    ExternalUserProfile,
    IdentityAuthCode,
    IntegrationCapability,
    IntegrationEventStatus,
    IntegrationPlatform,
    InteractiveCard,
    NotificationDeliveryResult,
    NotificationMessage,
    OrgSyncResult,
    ProviderHealthCheck,
    UserRecord,
)
from app.integrations.providers.generic_webhook import model_to_payload, utc_now


class LocalIntegrationProvider(
    NotificationProvider,
    IdentityProvider,
    OrgProvider,
    ApprovalProvider,
    BusinessSystemProvider,
):
    """本地演示 Provider。

    它不连接外部平台，只把通知、审批和业务同步写入 context.config 中的内存列表，
    用于本地演示、测试和没有企业平台账号时的 PoC。
    """

    platform = IntegrationPlatform.LOCAL
    capabilities = frozenset(
        {
            IntegrationCapability.NOTIFICATION,
            IntegrationCapability.IDENTITY,
            IntegrationCapability.ORG,
            IntegrationCapability.APPROVAL,
            IntegrationCapability.BUSINESS,
        }
    )

    def health_check(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(
            platform=self.platform,
            healthy=True,
            message="本地演示 Provider 可用，不会访问外部平台。",
            checked_at=utc_now(),
        )

    def send_message(self, message: NotificationMessage) -> NotificationDeliveryResult:
        outbox = self._outbox()
        outbox.append({"type": "message", "payload": model_to_payload(message)})
        return NotificationDeliveryResult(
            success=True,
            provider_message_id=f"local-message-{len(outbox)}",
            metadata={"mode": "local", "outbox_size": len(outbox)},
        )

    def send_interactive_card(self, card: InteractiveCard) -> NotificationDeliveryResult:
        outbox = self._outbox()
        outbox.append({"type": "interactive_card", "payload": model_to_payload(card)})
        return NotificationDeliveryResult(
            success=True,
            provider_message_id=f"local-card-{len(outbox)}",
            metadata={"mode": "local", "outbox_size": len(outbox)},
        )

    def exchange_code_for_user(self, auth_code: IdentityAuthCode) -> ExternalUserProfile:
        user = self._find_user(auth_code.code) or self._demo_users()[0]
        return self._to_profile(user)

    def get_user_profile(self, external_user_id: str) -> ExternalUserProfile:
        user = self._find_user(external_user_id) or {
            "external_user_id": external_user_id,
            "name": "本地演示用户",
            "external_department_ids": ["D001"],
            "position": "员工",
            "active": True,
        }
        return self._to_profile(user)

    def list_departments(self) -> list[DepartmentRecord]:
        return [DepartmentRecord(**department) for department in self._demo_departments()]

    def list_users(self, department_external_id: str | None = None) -> list[UserRecord]:
        users = self._demo_users()
        if department_external_id:
            users = [
                user
                for user in users
                if department_external_id in user.get("external_department_ids", [])
            ]
        return [UserRecord(**user) for user in users]

    def sync_all(self) -> OrgSyncResult:
        result = super().sync_all()
        result.message = "本地演示组织架构已读取。"
        return result

    def create_approval_task(self, payload: ApprovalTaskPayload) -> ApprovalTaskResult:
        external_id = f"LOCAL-APPROVAL-{payload.approval_id}"
        self._approvals().append({"external_id": external_id, "payload": model_to_payload(payload)})
        return ApprovalTaskResult(
            success=True,
            external_approval_id=external_id,
            external_task_id=f"LOCAL-TASK-{payload.approval_id}",
            message="本地审批任务已创建。",
        )

    def parse_callback(self, payload: dict) -> ApprovalCallbackEvent:
        try:
            action = ApprovalCallbackAction(str(payload["action"]))
        except (KeyError, ValueError) as exc:
            raise IntegrationCallbackVerificationError(
                "本地审批回调缺少合法 action。",
                details={"payload_keys": sorted(payload.keys())},
            ) from exc

        approval_id = payload.get("local_approval_id") or payload.get("approval_id")
        return ApprovalCallbackEvent(
            platform=self.platform,
            external_approval_id=payload.get("external_approval_id"),
            local_approval_id=int(approval_id) if approval_id is not None else None,
            actor_external_user_id=payload.get("actor_external_user_id", "local-user-001"),
            action=action,
            comment=payload.get("comment"),
            raw_payload=payload,
        )

    def push_business_object(self, payload: BusinessSyncPayload) -> BusinessSyncResult:
        external_id = f"LOCAL-{payload.object_type.value.upper()}-{payload.local_id}"
        business_events = self._business_events()
        business_events.append({"external_id": external_id, "payload": model_to_payload(payload)})
        return BusinessSyncResult(
            success=True,
            external_id=external_id,
            sync_status=IntegrationEventStatus.SUCCESS,
            raw_response={"mode": "local", "business_event_count": len(business_events)},
        )

    def sync_status(self, object_type: str, external_id: str) -> BusinessSyncResult:
        return BusinessSyncResult(
            success=True,
            external_id=external_id,
            sync_status=IntegrationEventStatus.SUCCESS,
            raw_response={"object_type": object_type, "status": "synced_from_local_demo"},
        )

    def _outbox(self) -> list[dict]:
        return self.context.config.setdefault("local_outbox", [])

    def _approvals(self) -> list[dict]:
        return self.context.config.setdefault("local_approvals", [])

    def _business_events(self) -> list[dict]:
        return self.context.config.setdefault("local_business_events", [])

    def _demo_departments(self) -> list[dict]:
        return self.context.config.get(
            "demo_departments",
            [
                {"external_department_id": "D001", "name": "制造中心"},
                {"external_department_id": "D002", "name": "质量部", "parent_external_department_id": "D001"},
                {"external_department_id": "D003", "name": "设备部", "parent_external_department_id": "D001"},
                {"external_department_id": "D004", "name": "采购部"},
            ],
        )

    def _demo_users(self) -> list[dict]:
        return self.context.config.get(
            "demo_users",
            [
                {
                    "external_user_id": "local-user-001",
                    "name": "张工",
                    "external_department_ids": ["D003"],
                    "position": "设备工程师",
                    "active": True,
                },
                {
                    "external_user_id": "local-user-002",
                    "name": "李经理",
                    "external_department_ids": ["D002"],
                    "position": "质量主管",
                    "active": True,
                },
                {
                    "external_user_id": "local-user-003",
                    "name": "王主管",
                    "external_department_ids": ["D004"],
                    "position": "采购主管",
                    "active": True,
                },
            ],
        )

    def _find_user(self, external_user_id: str) -> dict | None:
        return next(
            (user for user in self._demo_users() if user.get("external_user_id") == external_user_id),
            None,
        )

    def _to_profile(self, user: dict) -> ExternalUserProfile:
        return ExternalUserProfile(
            external_user_id=user["external_user_id"],
            name=user["name"],
            enterprise_id=self.enterprise_id,
            external_department_ids=user.get("external_department_ids", []),
            position=user.get("position"),
            active=bool(user.get("active", True)),
            raw=user,
        )

from unittest import mock

import pytest

from app.integration import IntegrationMessage


def _sync_executor_submit(fn, *args, **kwargs):
    """Run the submitted function synchronously to avoid thread race in tests."""
    fn(*args, **kwargs)


class TestNotificationOnApproval:
    def test_create_approval_triggers_notification(self, db_session):
        mock_adapter = mock.MagicMock()
        with mock.patch(
            "app.services.notification_service.get_integration_adapter",
            return_value=mock_adapter,
        ), mock.patch("app.services.notification_service.settings.integration_enabled", True), mock.patch(
            "app.services.notification_service._executor.submit",
            side_effect=_sync_executor_submit,
        ):
            from app.services.approval_service import create_approval
            from app.schemas.approval import ApprovalCreateRequest

            create_approval(
                db_session,
                ApprovalCreateRequest(
                    action_type="create_purchase_request",
                    action_payload={"item_name": "滤芯", "quantity": 5, "reason": "保养"},
                ),
            )
            mock_adapter.send.assert_called()
            message = mock_adapter.send.call_args[0][0]
            assert "审批" in message.title
            assert "create_purchase_request" in message.title
            assert "第 1 级" in message.content
            assert "部门负责人审批" in message.content

    def test_approve_triggers_notification(self, db_session):
        mock_adapter = mock.MagicMock()
        with mock.patch(
            "app.services.notification_service.get_integration_adapter",
            return_value=mock_adapter,
        ), mock.patch("app.services.notification_service.settings.integration_enabled", True), mock.patch(
            "app.services.notification_service._executor.submit",
            side_effect=_sync_executor_submit,
        ):
            from app.services.approval_service import create_approval, approve_approval
            from app.schemas.approval import ApprovalCreateRequest, ApprovalDecisionRequest

            approval = create_approval(
                db_session,
                ApprovalCreateRequest(
                    action_type="create_maintenance_ticket",
                    action_payload={
                        "ticket_type": "设备维修",
                        "title": "空压机故障",
                        "description": "E07报警",
                    },
                ),
            )
            mock_adapter.send.reset_mock()

            approve_approval(
                db_session, approval.id,
                ApprovalDecisionRequest(reviewer="manager_zhang", comment="同意"),
                current_user_role="manager",
            )
            mock_adapter.send.assert_called()
            message = mock_adapter.send.call_args[0][0]
            assert "审批" in message.title
            assert "已全部通过" in message.content
            assert "create_maintenance_ticket" in message.title

    def test_reject_triggers_notification(self, db_session):
        mock_adapter = mock.MagicMock()
        with mock.patch(
            "app.services.notification_service.get_integration_adapter",
            return_value=mock_adapter,
        ), mock.patch("app.services.notification_service.settings.integration_enabled", True), mock.patch(
            "app.services.notification_service._executor.submit",
            side_effect=_sync_executor_submit,
        ):
            from app.services.approval_service import create_approval, reject_approval
            from app.schemas.approval import ApprovalCreateRequest, ApprovalDecisionRequest

            approval = create_approval(
                db_session,
                ApprovalCreateRequest(
                    action_type="create_purchase_request",
                    action_payload={"item_name": "滤芯", "quantity": 5, "reason": "保养"},
                ),
            )
            mock_adapter.send.reset_mock()

            reject_approval(
                db_session, approval.id,
                ApprovalDecisionRequest(reviewer="manager_zhang", comment="预算不足"),
            )
            mock_adapter.send.assert_called()
            message = mock_adapter.send.call_args[0][0]
            assert "审批" in message.title
            assert "manager_zhang" in message.content
            assert "预算不足" in message.content
            assert "第 1 级" in message.content

    def test_integration_disabled_skips_notification(self, db_session):
        with mock.patch(
            "app.services.notification_service.settings.integration_enabled", False
        ), mock.patch("app.services.notification_service.get_integration_adapter") as mock_get:
            from app.services.approval_service import create_approval
            from app.schemas.approval import ApprovalCreateRequest

            create_approval(
                db_session,
                ApprovalCreateRequest(
                    action_type="create_purchase_request",
                    action_payload={"item_name": "滤芯", "quantity": 5, "reason": "保养"},
                ),
            )
            mock_get.assert_not_called()


class TestNotificationOnSLA:
    def test_sla_breach_triggers_notification(self, db_session):
        from datetime import datetime, timedelta, timezone

        from app.models.ticket import Ticket
        from app.models.base import TicketStatus, TaskPriority

        ticket = Ticket(
            ticket_type="设备维修",
            title="超时工单",
            description="测试",
            priority=TaskPriority.URGENT,
            status=TicketStatus.OPEN,
            sla_hours=2,
            sla_deadline=datetime.now(timezone.utc) - timedelta(hours=1),
            sla_breached=False,
        )
        db_session.add(ticket)
        db_session.commit()

        mock_adapter = mock.MagicMock()
        with mock.patch(
            "app.services.notification_service.get_integration_adapter",
            return_value=mock_adapter,
        ), mock.patch("app.services.notification_service.settings.integration_enabled", True), mock.patch(
            "app.services.notification_service._executor.submit",
            side_effect=_sync_executor_submit,
        ):
            from app.services.sla_service import check_sla_breach

            breached = check_sla_breach(db_session)
            assert len(breached) >= 1
            mock_adapter.send.assert_called()
            message = mock_adapter.send.call_args[0][0]
            assert "SLA" in message.title
            assert "超时工单" in message.content
            assert "设备维修" in message.content

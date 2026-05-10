# 企微/钉钉通知集成 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已有的 WeComAdapter/DingTalkAdapter 通过 NotificationService 异步接入审批创建、审批完成、SLA 超时三个业务触发点。

**Architecture:** 新建 `NotificationService` 单例，内部用 `ThreadPoolExecutor(max_workers=2)` 执行 fire-and-forget 异步发送。业务代码只调用 `notify(IntegrationMessage)`，无需感知具体平台。通知失败只记日志，不抛异常。

**Tech Stack:** Python stdlib `ThreadPoolExecutor`、现有 `IntegrationAdapter` ABC、pytest + unittest.mock

---

## File Structure

```
backend/
├── app/
│   ├── core/
│   │   └── config.py                      # MODIFY: +integration_platform
│   └── services/
│       ├── notification_service.py         # CREATE: NotificationService singleton
│       ├── approval_service.py             # MODIFY: add notify() at 3 hook points
│       └── sla_service.py                 # MODIFY: add notify() in check_sla_breach
└── tests/
    └── test_notification.py               # CREATE: 5 tests
```

---

### Task 1: Add config field and create NotificationService

**Files:**
- Modify: `app/core/config.py`
- Create: `app/services/notification_service.py`

- [ ] **Step 1: Add `integration_platform` config**

In `app/core/config.py`, add one line after `integration_enabled` (line 64):

```python
    integration_enabled: bool = Field(default=False, alias="INTEGRATION_ENABLED")
    integration_platform: str = Field(default="wecom", alias="INTEGRATION_PLATFORM")
```

- [ ] **Step 2: Create notification_service.py**

```python
# app/services/notification_service.py
import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.integration import IntegrationMessage, get_integration_adapter

_logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)


def notify(message: IntegrationMessage) -> None:
    """Fire-and-forget async notification. Errors are logged, never raised."""
    if not settings.integration_enabled:
        return
    adapter = get_integration_adapter(settings.integration_platform)
    if adapter is None:
        return
    _executor.submit(_send_and_log, adapter, message)


def _send_and_log(adapter, message: IntegrationMessage) -> None:
    try:
        adapter.send(message)
    except Exception:
        _logger.exception("Notification failed via %s", adapter.platform_name)
```

- [ ] **Step 3: Verify module imports cleanly**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -c "from app.services.notification_service import notify; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/core/config.py app/services/notification_service.py
git commit -m "feat: add NotificationService with ThreadPoolExecutor"
```

---

### Task 2: Write failing notification tests

**Files:**
- Create: `tests/test_notification.py`

- [ ] **Step 1: Write all 5 tests**

```python
# tests/test_notification.py
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app.integration import IntegrationMessage
from app.main import app

client = TestClient(app)


class TestNotificationOnApproval:
    def test_create_approval_triggers_notification(self, db_session):
        mock_adapter = mock.MagicMock()
        with mock.patch(
            "app.services.notification_service.get_integration_adapter",
            return_value=mock_adapter,
        ), mock.patch("app.services.notification_service.settings.integration_enabled", True):
            from app.services.approval_service import create_approval
            from app.schemas.approval import ApprovalCreateRequest

            create_approval(
                db_session,
                ApprovalCreateRequest(
                    action_type="create_purchase_request",
                    action_payload={"item_name": "滤芯", "quantity": 5, "reason": "保养"},
                ),
            )
            # Notification submitted to thread pool — call send on mock directly
            # Since notify() uses ThreadPoolExecutor.submit(), we assert
            # mock_adapter.send was called at least once
            assert mock_adapter.send.called

    def test_approve_triggers_notification(self, db_session):
        mock_adapter = mock.MagicMock()
        with mock.patch(
            "app.services.notification_service.get_integration_adapter",
            return_value=mock_adapter,
        ), mock.patch("app.services.notification_service.settings.integration_enabled", True):
            from app.services.approval_service import create_approval, approve_approval
            from app.schemas.approval import ApprovalCreateRequest, ApprovalDecisionRequest

            # Create a single-level approval (maintenance_ticket = 1 level)
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
            # Clear mock call history from create_approval
            mock_adapter.send.reset_mock()

            # Approve (single level chain → completes immediately)
            approve_approval(
                db_session, approval.id,
                ApprovalDecisionRequest(reviewer="manager_zhang", comment="同意"),
                current_user_role="manager",
            )
            assert mock_adapter.send.called

    def test_reject_triggers_notification(self, db_session):
        mock_adapter = mock.MagicMock()
        with mock.patch(
            "app.services.notification_service.get_integration_adapter",
            return_value=mock_adapter,
        ), mock.patch("app.services.notification_service.settings.integration_enabled", True):
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
            assert mock_adapter.send.called

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

        # Create ticket with past SLA deadline
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
        ), mock.patch("app.services.notification_service.settings.integration_enabled", True):
            from app.services.sla_service import check_sla_breach

            breached = check_sla_breach(db_session)
            assert len(breached) >= 1
            assert mock_adapter.send.called
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/test_notification.py -v
```

Expected: FAIL — notification_service has no `notify` wiring yet (some may fail due to missing import/mock targets).

- [ ] **Step 3: Commit**

```bash
git add tests/test_notification.py
git commit -m "test: add failing notification tests for approval and SLA breach"
```

---

### Task 3: Wire notify() into business logic

**Files:**
- Modify: `app/services/approval_service.py`
- Modify: `app/services/sla_service.py`

- [ ] **Step 1: Add imports at top of approval_service.py**

At line 2 (after `from typing import Any`), add:

```python
from app.integration import IntegrationMessage
from app.services.notification_service import notify
```

- [ ] **Step 2: Add notify() in create_approval(), before the return**

Replace the `return approval` in `create_approval()` (currently line 56) with:

```python
    notify(IntegrationMessage(
        title=f"新审批提交 — {data.action_type}",
        content=f"审批 #{approval.id} 已提交，当前待第 1 级审批。",
    ))
    return approval
```

- [ ] **Step 3: Add notify() in approve_approval(), chain-advance branch**

Replace the `return approval` in the chain-advance block (currently line 142) with:

```python
        notify(IntegrationMessage(
            title=f"审批推进 — 第 {approval.current_level}/{total_levels} 级",
            content=f"审批 #{approval_id} 已进入第 {approval.current_level}/{total_levels} 级审批。",
        ))
        return approval
```

- [ ] **Step 4: Add notify() in approve_approval(), final-approval branch**

After the successful final approval block (after `db.refresh(approval)`, currently around line 178), before `return approval`:

```python
    notify(IntegrationMessage(
        title=f"审批通过 — {approval.action_type}",
        content=f"审批 #{approval_id} 已全部通过，业务动作已执行。",
    ))
    return approval
```

- [ ] **Step 5: Add notify() in reject_approval(), before return**

Replace the `return approval` in `reject_approval()` (currently line 195) with:

```python
    notify(IntegrationMessage(
        title=f"审批拒绝 — {approval.action_type}",
        content=f"审批 #{approval_id} 已被 {data.reviewer} 拒绝。原因：{data.comment or '无'}",
    ))
    return approval
```

- [ ] **Step 6: Wire notify() in sla_service.py**

Add import at top of `app/services/sla_service.py`:

```python
from app.integration import IntegrationMessage
from app.services.notification_service import notify
```

In `check_sla_breach()`, after the `for ticket in breached:` loop that sets `sla_breached = True`, and before `return list(breached)` (currently line 55), add:

```python
    for ticket in breached:
        notify(IntegrationMessage(
            title=f"SLA 超时 — 工单 #{ticket.id}",
            content=(
                f"工单 #{ticket.id}「{ticket.title}」SLA 已超时。\n"
                f"类型：{ticket.ticket_type}，创建时间：{ticket.created_at}"
            ),
        ))
```

- [ ] **Step 7: Run notification tests**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/test_notification.py -v
```

Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add app/services/approval_service.py app/services/sla_service.py
git commit -m "feat: wire async notifications into approval and SLA workflows"
```

---

### Task 4: Final verification

- [ ] **Step 1: Run full test suite**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/ -v --ignore=tests/test_ingest_demo_docs.py --ignore=tests/test_seed_demo_data.py
```

Expected: 140 passed (135 + 5 new), 1 skipped.

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "chore: final verification — 140 tests passing with notification integration"
```

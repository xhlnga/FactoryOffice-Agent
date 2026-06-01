from app.integrations.callbacks.feishu_callback import FeishuCallbackHandler
from app.integrations.core.schemas import ApprovalCallbackAction


def test_callback_event_id_is_idempotent() -> None:
    """同一个外部事件 ID 重复回调时只能处理一次。"""
    handler = FeishuCallbackHandler(verification_token="verify-token")
    payload = {
        "token": "verify-token",
        "header": {"event_type": "card.action.trigger", "event_id": "EVT-IDEMPOTENT-001"},
        "event": {
            "local_approval_id": 18,
            "action": "approve",
            "operator_id": "ou_xxx",
        },
    }

    first = handler.handle_event(payload)
    second = handler.handle_event(payload)

    assert first.duplicated is False
    assert first.approval_event is not None
    assert first.approval_event.action == ApprovalCallbackAction.APPROVE
    assert second.duplicated is True
    assert second.approval_event is None


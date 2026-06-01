import hashlib
import unittest

from app.integrations.callbacks.dingtalk_callback import DingTalkCallbackHandler
from app.integrations.callbacks.feishu_callback import FeishuCallbackHandler
from app.integrations.callbacks.wecom_callback import WeComCallbackHandler
from app.integrations.core.exceptions import IntegrationCallbackVerificationError
from app.integrations.core.schemas import ApprovalCallbackAction


class IntegrationCallbackTest(unittest.TestCase):
    """企业平台回调适配测试。"""

    def test_wecom_url_verification_checks_signature(self) -> None:
        token = "token-001"
        timestamp = "1710000000"
        nonce = "nonce-001"
        echostr = "encrypted-echo"
        signature = hashlib.sha1("".join(sorted([token, timestamp, nonce, echostr])).encode("utf-8")).hexdigest()

        result = WeComCallbackHandler(token=token, decrypt_echo=lambda value: f"plain:{value}").verify_url(
            {
                "msg_signature": signature,
                "timestamp": timestamp,
                "nonce": nonce,
                "echostr": echostr,
            }
        )

        self.assertEqual(result.event_type, "url_verification")
        self.assertFalse(result.needs_decryption)
        self.assertEqual(result.response_body, f"plain:{echostr}")

    def test_wecom_url_verification_without_decryptor_does_not_return_encrypted_echo(self) -> None:
        token = "token-001"
        timestamp = "1710000000"
        nonce = "nonce-001"
        echostr = "encrypted-echo"
        signature = hashlib.sha1("".join(sorted([token, timestamp, nonce, echostr])).encode("utf-8")).hexdigest()

        result = WeComCallbackHandler(token=token).verify_url(
            {
                "msg_signature": signature,
                "timestamp": timestamp,
                "nonce": nonce,
                "echostr": echostr,
            }
        )

        self.assertTrue(result.needs_decryption)
        self.assertIsNone(result.response_body)

    def test_wecom_invalid_signature_is_rejected(self) -> None:
        handler = WeComCallbackHandler(token="token-001")

        with self.assertRaises(IntegrationCallbackVerificationError):
            handler.verify_url(
                {
                    "msg_signature": "bad",
                    "timestamp": "1710000000",
                    "nonce": "nonce-001",
                    "echostr": "encrypted-echo",
                }
            )

    def test_dingtalk_approval_callback_maps_to_internal_event_and_is_idempotent(self) -> None:
        handler = DingTalkCallbackHandler(callback_token="callback-token")
        payload = {
            "token": "callback-token",
            "EventType": "bpms_task_change",
            "processInstanceId": "PROC-001",
            "approval_id": 12,
            "action": "approve",
            "staffId": "ding-user-001",
        }

        first = handler.handle_event(payload)
        second = handler.handle_event(payload)

        self.assertFalse(first.duplicated)
        self.assertIsNotNone(first.approval_event)
        self.assertEqual(first.approval_event.action, ApprovalCallbackAction.APPROVE)
        self.assertTrue(second.duplicated)
        self.assertEqual(second.response_body, {"success": True})

    def test_dingtalk_callback_token_mismatch_is_rejected(self) -> None:
        handler = DingTalkCallbackHandler(callback_token="right-token")

        with self.assertRaises(IntegrationCallbackVerificationError):
            handler.handle_event({"token": "wrong-token", "EventType": "bpms_task_change"})

    def test_dingtalk_encrypted_callback_requires_decryption_before_ack(self) -> None:
        result = DingTalkCallbackHandler().handle_event({"encrypt": "encrypted-payload"})

        self.assertTrue(result.needs_decryption)
        self.assertIsNone(result.response_body)

    def test_feishu_url_challenge_returns_challenge(self) -> None:
        result = FeishuCallbackHandler(verification_token="verify-token").handle_event(
            {
                "type": "url_verification",
                "token": "verify-token",
                "challenge": "challenge-value",
            }
        )

        self.assertEqual(result.response_body, {"challenge": "challenge-value"})
        self.assertEqual(result.event_type, "url_verification")

    def test_feishu_encrypted_callback_requires_decryption_before_ack(self) -> None:
        result = FeishuCallbackHandler().handle_event({"encrypt": "encrypted-payload"})

        self.assertTrue(result.needs_decryption)
        self.assertIsNone(result.response_body)

    def test_feishu_event_is_idempotent_and_maps_approval_action(self) -> None:
        handler = FeishuCallbackHandler(verification_token="verify-token")
        payload = {
            "token": "verify-token",
            "header": {"event_type": "card.action.trigger", "event_id": "EVT-001"},
            "event": {
                "local_approval_id": 18,
                "action": "reject",
                "operator_id": "ou_xxx",
                "comment": "预算说明不足。",
            },
        }

        first = handler.handle_event(payload)
        second = handler.handle_event(payload)

        self.assertFalse(first.duplicated)
        self.assertIsNotNone(first.approval_event)
        self.assertEqual(first.approval_event.action, ApprovalCallbackAction.REJECT)
        self.assertTrue(second.duplicated)


if __name__ == "__main__":
    unittest.main()

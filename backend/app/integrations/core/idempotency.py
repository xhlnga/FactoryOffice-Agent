import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.integrations.core.schemas import IdempotencyCheckResult


def build_idempotency_key(
    *,
    provider: str,
    event_type: str,
    external_event_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    """生成幂等键。

    优先使用外部平台事件 ID；如果平台没有稳定事件 ID，则使用规范化 payload
    的哈希。这样可以降低重复回调、重复通知导致重复审批或重复写入的风险。
    """
    if external_event_id:
        raw = f"{provider}:{event_type}:{external_event_id}"
    else:
        raw_payload = _stable_json(payload or {})
        raw = f"{provider}:{event_type}:{raw_payload}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{provider}:{event_type}:{digest}"


def build_business_idempotency_key(
    *,
    provider: str,
    object_type: str,
    local_id: int | str,
    action: str,
) -> str:
    """生成业务同步幂等键。"""
    raw = f"{provider}:{object_type}:{local_id}:{action}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{provider}:{object_type}:{action}:{digest}"


@dataclass
class InMemoryIdempotencyStore:
    """内存幂等存储。

    仅用于本地开发和单进程测试。生产环境应替换为数据库表或 Redis，并设置唯一索引。
    """

    ttl_seconds: int = 3600
    _records: dict[str, tuple[datetime, dict[str, Any] | None]] = field(default_factory=dict)

    def check(self, key: str) -> IdempotencyCheckResult:
        """检查幂等键是否已经处理过。"""
        self._purge_expired()
        record = self._records.get(key)
        if record is None:
            return IdempotencyCheckResult(key=key, duplicated=False)
        _, previous_result = record
        return IdempotencyCheckResult(
            key=key,
            duplicated=True,
            reason="幂等键已存在，当前事件可能是重复回调或重复投递。",
            previous_result=previous_result,
        )

    def mark_processed(self, key: str, result: dict[str, Any] | None = None) -> IdempotencyCheckResult:
        """标记幂等键已处理。"""
        check_result = self.check(key)
        if check_result.duplicated:
            return check_result
        self._records[key] = (datetime.now(timezone.utc), result)
        return IdempotencyCheckResult(key=key, duplicated=False, previous_result=result)

    def _purge_expired(self) -> None:
        """清理过期幂等记录。"""
        if self.ttl_seconds <= 0:
            return
        expire_before = datetime.now(timezone.utc) - timedelta(seconds=self.ttl_seconds)
        expired_keys = [
            key
            for key, (created_at, _) in self._records.items()
            if created_at < expire_before
        ]
        for key in expired_keys:
            self._records.pop(key, None)


def _stable_json(payload: dict[str, Any]) -> str:
    """稳定序列化 payload，避免字段顺序导致幂等键变化。"""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

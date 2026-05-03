from datetime import datetime
from secrets import token_hex
from uuid import uuid4


PREFIXES = {
    "document": "DOC",
    "task": "TASK",
    "ticket": "TICKET",
    "purchase": "PR",
    "approval": "APR",
    "audit": "AUDIT",
}


def uuid_hex() -> str:
    """生成无连字符 UUID，适合文件名和内部追踪。"""
    return uuid4().hex


def random_token(length: int = 16) -> str:
    """生成随机短 token；length 表示十六进制字符长度。"""
    if length < 8:
        raise ValueError("随机 token 长度不能小于 8。")
    return token_hex(length // 2)


def build_business_id(kind: str, *, now: datetime | None = None) -> str:
    """生成可读业务编号，便于日志、演示和人工排查。

    示例：PR-20260502-A1B2C3。
    """
    prefix = PREFIXES.get(kind, kind.upper())
    current = now or datetime.now()
    return f"{prefix}-{current:%Y%m%d}-{random_token(8).upper()}"

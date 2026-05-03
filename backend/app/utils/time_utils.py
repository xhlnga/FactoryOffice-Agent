from datetime import UTC, date, datetime


def utc_now() -> datetime:
    """返回带时区的 UTC 当前时间。"""
    return datetime.now(UTC)


def to_iso_datetime(value: datetime | None) -> str | None:
    """把时间转换为 ISO 字符串，空值保持为空。"""
    return value.isoformat() if value else None


def parse_iso_date(value: str | None) -> date | None:
    """只解析 ISO 日期；中文自然语言日期由上层流程保留为文本。"""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None

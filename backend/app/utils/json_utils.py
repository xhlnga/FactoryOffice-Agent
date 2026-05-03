import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any


def to_jsonable(value: Any) -> Any:
    """把常见 Python 对象转换为可 JSON 序列化的结构。"""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [to_jsonable(item) for item in value]
    return value


def dumps_json(value: Any, *, indent: int | None = None) -> str:
    """稳定输出 JSON 字符串，保留中文。"""
    return json.dumps(
        to_jsonable(value),
        ensure_ascii=False,
        indent=indent,
        sort_keys=True,
    )


def loads_json_object(raw: str) -> dict[str, Any]:
    """解析 JSON 对象；不是对象时抛出 ValueError。"""
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON 内容必须是对象。")
    return data

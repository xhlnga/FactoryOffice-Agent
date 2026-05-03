"""导入 data/seed 下的演示业务数据。

用法：
    python3 scripts/seed_demo_data.py

说明：
    本脚本用于本地演示和开发联调，把用户、任务、工单、采购申请、
    审批记录和审计日志写入数据库。若相同 ID 已存在，则更新现有记录，
    便于重复执行。
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
SEED_DIR = PROJECT_ROOT / "data" / "seed"

sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.approval import Approval  # noqa: E402
from app.models.base import (  # noqa: E402
    ApprovalStatus,
    AuditStatus,
    PurchaseStatus,
    TaskPriority,
    TaskStatus,
    TicketStatus,
    UserRole,
)
from app.models.purchase_request import PurchaseRequest  # noqa: E402
from app.models.task import Task  # noqa: E402
from app.models.ticket import Ticket  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> None:
    """导入全部 seed 数据。"""
    if not SEED_DIR.exists():
        raise SystemExit(f"seed 目录不存在：{SEED_DIR}")

    try:
        with SessionLocal() as db:
            imported = {
                "users": upsert_records(db, User, load_json("users.json"), user_converter),
                "tasks": upsert_records(db, Task, load_json("tasks.json"), task_converter),
                "tickets": upsert_records(db, Ticket, load_json("tickets.json"), ticket_converter),
                "purchase_requests": upsert_records(
                    db,
                    PurchaseRequest,
                    load_json("purchase_requests.json"),
                    purchase_converter,
                ),
                "approvals": upsert_records(db, Approval, load_json("approvals.json"), approval_converter),
                "audit_logs": upsert_records(db, AuditLog, load_json("audit_logs.json"), audit_log_converter),
            }
            reset_id_sequences(db)
            db.commit()
    except SQLAlchemyError as exc:
        raise SystemExit(
            "\n数据库连接或写入失败。\n"
            "请确认 PostgreSQL 已启动、迁移已执行，并根据运行位置使用正确 DATABASE_URL：\n"
            "- 宿主机运行脚本：postgresql+psycopg://factory_user:factory_pass@localhost:5432/factory_agent\n"
            "- Docker backend 容器内运行：postgresql+psycopg://factory_user:factory_pass@postgres:5432/factory_agent\n"
            f"原始错误：{exc}\n"
        ) from exc

    print("演示业务数据导入完成：")
    for name, count in imported.items():
        print(f"- {name}: {count} 条")


def load_json(filename: str) -> list[dict[str, Any]]:
    """读取 seed JSON 文件。"""
    path = SEED_DIR / filename
    if not path.exists():
        raise SystemExit(f"seed 文件不存在：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_records(db, model, rows: list[dict[str, Any]], converter) -> int:
    """按 ID 更新或插入记录。"""
    for row in rows:
        values = converter(row)
        record = db.get(model, values["id"])
        if record is None:
            db.add(model(**values))
            continue
        for field, value in values.items():
            setattr(record, field, value)
    return len(rows)


def reset_id_sequences(db) -> None:
    """校准 PostgreSQL 自增序列，避免 seed 固定 ID 之后新建记录撞主键。"""
    table_names = [
        "users",
        "tasks",
        "tickets",
        "purchase_requests",
        "approvals",
        "audit_logs",
    ]
    for table_name in table_names:
        db.execute(
            text(
                """
                SELECT setval(
                    pg_get_serial_sequence(:table_name, 'id'),
                    COALESCE((SELECT MAX(id) FROM """ + table_name + """), 1),
                    true
                )
                """
            ),
            {"table_name": table_name},
        )


def user_converter(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "role": UserRole(row["role"]),
        "created_at": parse_datetime(row["created_at"]),
    }


def task_converter(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "due_date": parse_date(row.get("due_date")),
        "priority": TaskPriority(row["priority"]),
        "status": TaskStatus(row["status"]),
        "created_at": parse_datetime(row["created_at"]),
    }


def ticket_converter(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "priority": TaskPriority(row["priority"]),
        "status": TicketStatus(row["status"]),
        "created_at": parse_datetime(row["created_at"]),
    }


def purchase_converter(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "status": PurchaseStatus(row["status"]),
        "created_at": parse_datetime(row["created_at"]),
    }


def approval_converter(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "status": ApprovalStatus(row["status"]),
        "reviewed_at": parse_datetime(row.get("reviewed_at")),
        "executed_at": parse_datetime(row.get("executed_at")),
        "created_at": parse_datetime(row["created_at"]),
    }


def audit_log_converter(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "status": AuditStatus(row["status"]),
        "created_at": parse_datetime(row["created_at"]),
    }


def parse_datetime(value: str | None) -> datetime | None:
    """解析 ISO 时间字符串。"""
    if value is None:
        return None
    return datetime.fromisoformat(value)


def parse_date(value: str | None) -> date | None:
    """解析 ISO 日期字符串。"""
    if value is None:
        return None
    return date.fromisoformat(value)


if __name__ == "__main__":
    main()

from typing import Any


def append_trace_step(
    trace_steps: list[dict[str, Any]] | None,
    *,
    step: str,
    status: str,
    detail: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """追加 Agent Trace 步骤。

    Trace 面向调试和审计，用来说明 Agent 为什么进入某个 SOP、缺哪些字段、
    是否需要审批以及下一步状态是什么。
    """
    return [
        *(trace_steps or []),
        {
            "step": step,
            "status": status,
            "detail": detail or {},
        },
    ]


def summarize_trace(trace_steps: list[dict[str, Any]] | None) -> list[str]:
    """把结构化 Trace 转成简短文本。"""
    summary: list[str] = []
    for step in trace_steps or []:
        name = step.get("step", "unknown")
        status = step.get("status", "unknown")
        detail = step.get("detail") or {}
        if "intent" in detail:
            summary.append(f"{name}: {status}, intent={detail['intent']}")
        elif "sop_name" in detail:
            summary.append(f"{name}: {status}, sop={detail['sop_name']}")
        else:
            summary.append(f"{name}: {status}")
    return summary


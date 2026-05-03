from typing import Any

from app.agents.factory_office_agent import run_factory_office_agent
from app.evaluators.test_cases import (
    DEFAULT_WORKFLOW_EVAL_CASES,
    EvalFinding,
    EvalResult,
    WorkflowEvalCase,
)
from app.workflows.maintenance_ticket import generate_maintenance_ticket
from app.workflows.meeting_to_tasks import generate_task_drafts
from app.workflows.purchase_request import generate_purchase_request
from app.workflows.quality_issue import generate_quality_issue_ticket
from app.workflows.weekly_report import generate_weekly_report
from app.utils.json_utils import dumps_json


def evaluate_workflow_case(case: WorkflowEvalCase) -> EvalResult:
    """评测单条 Agent 路由或固定办公流程用例。"""
    output = _run_case(case)
    findings = [
        _check_intent(case, output),
        _check_requires_approval(case, output),
        _check_workflow_status(case, output),
        _check_missing_fields(case, output),
        _check_output_keywords(case, output),
        _check_forbidden_output_keywords(case, output),
    ]
    return _build_result(case.case_id, findings)


def run_default_workflow_eval() -> list[EvalResult]:
    """运行默认办公流程评测。"""
    return [evaluate_workflow_case(case) for case in DEFAULT_WORKFLOW_EVAL_CASES]


def _run_case(case: WorkflowEvalCase) -> dict[str, Any]:
    """根据用例类型执行对应流程。"""
    if case.workflow_name == "agent_routing":
        return dict(run_factory_office_agent(case.input_text))

    if case.workflow_name == "meeting_to_tasks":
        return generate_task_drafts(case.input_text).model_dump(mode="json")

    if case.workflow_name == "maintenance_ticket":
        return generate_maintenance_ticket(case.input_text).model_dump(mode="json")

    if case.workflow_name == "quality_issue":
        return generate_quality_issue_ticket(case.input_text).model_dump(mode="json")

    if case.workflow_name == "purchase_request":
        return generate_purchase_request(case.input_text).model_dump(mode="json")

    if case.workflow_name == "weekly_report":
        return generate_weekly_report(case.input_text).model_dump(mode="json")

    raise ValueError(f"未知流程类型：{case.workflow_name}")


def _check_intent(case: WorkflowEvalCase, output: dict[str, Any]) -> EvalFinding:
    """检查 Agent 是否把业务场景分到正确入口。"""
    if case.expected_intent is None:
        return EvalFinding(True, "intent", "该用例不检查意图。")

    actual = output.get("intent")
    return EvalFinding(
        passed=actual == case.expected_intent,
        check_name="intent",
        message="意图识别符合预期。" if actual == case.expected_intent else "意图识别不符合企业场景。",
        details={"expected": case.expected_intent, "actual": actual},
    )


def _check_requires_approval(case: WorkflowEvalCase, output: dict[str, Any]) -> EvalFinding:
    """检查是否正确进入人工确认。"""
    if case.expected_requires_approval is None:
        return EvalFinding(True, "requires_approval", "该用例不检查审批要求。")

    actual = output.get("requires_approval")
    return EvalFinding(
        passed=actual is case.expected_requires_approval,
        check_name="requires_approval",
        message="审批判断符合预期。" if actual is case.expected_requires_approval else "审批判断不符合企业流程。",
        details={"expected": case.expected_requires_approval, "actual": actual},
    )


def _check_workflow_status(case: WorkflowEvalCase, output: dict[str, Any]) -> EvalFinding:
    """检查流程状态，例如缺字段时不能进入草稿就绪。"""
    if case.expected_workflow_status is None:
        return EvalFinding(True, "workflow_status", "该用例不检查流程状态。")

    actual = output.get("workflow_status")
    return EvalFinding(
        passed=actual == case.expected_workflow_status,
        check_name="workflow_status",
        message="流程状态符合预期。" if actual == case.expected_workflow_status else "流程状态不符合企业流程。",
        details={"expected": case.expected_workflow_status, "actual": actual},
    )


def _check_missing_fields(case: WorkflowEvalCase, output: dict[str, Any]) -> EvalFinding:
    """检查采购等流程是否正确提示缺失字段。"""
    if not case.expected_missing_fields:
        return EvalFinding(True, "missing_fields", "该用例不检查缺失字段。")

    actual = set(output.get("missing_fields", []))
    expected = set(case.expected_missing_fields)
    missing = sorted(expected - actual)
    return EvalFinding(
        passed=not missing,
        check_name="missing_fields",
        message="缺失字段提示符合预期。" if not missing else "缺失字段提示不完整。",
        details={"expected": sorted(expected), "actual": sorted(actual), "missing": missing},
    )


def _check_output_keywords(case: WorkflowEvalCase, output: dict[str, Any]) -> EvalFinding:
    """检查输出是否包含关键业务信息。"""
    if not case.expected_output_keywords:
        return EvalFinding(True, "output_keywords", "该用例不检查输出关键词。")

    output_text = _stringify_output(output)
    missing = [keyword for keyword in case.expected_output_keywords if keyword not in output_text]
    return EvalFinding(
        passed=not missing,
        check_name="output_keywords",
        message="输出包含预期业务信息。" if not missing else "输出缺少预期业务信息。",
        details={"missing_keywords": missing},
    )


def _check_forbidden_output_keywords(case: WorkflowEvalCase, output: dict[str, Any]) -> EvalFinding:
    """检查输出是否出现现实业务中不应出现的内容。"""
    if not case.forbidden_output_keywords:
        return EvalFinding(True, "forbidden_output_keywords", "该用例不检查禁用关键词。")

    output_text = _stringify_output(output)
    matched = [keyword for keyword in case.forbidden_output_keywords if keyword in output_text]
    return EvalFinding(
        passed=not matched,
        check_name="forbidden_output_keywords",
        message="输出未出现禁用内容。" if not matched else "输出出现了不符合现实业务的内容。",
        details={"matched_keywords": matched},
    )


def _stringify_output(output: dict[str, Any]) -> str:
    """把流程输出转成可搜索文本。

    评测结构化结果时不检查 source/description 等原文承载字段，避免把用户原始输入误判为系统抽取错误。
    """
    return dumps_json(_remove_raw_text_fields(output))


def _remove_raw_text_fields(value: Any) -> Any:
    """移除原始输入字段，只保留系统生成或抽取出的结构化内容。"""
    raw_text_keys = {"source", "description", "input_text"}
    if isinstance(value, dict):
        return {
            key: _remove_raw_text_fields(item)
            for key, item in value.items()
            if key not in raw_text_keys
        }
    if isinstance(value, list):
        return [_remove_raw_text_fields(item) for item in value]
    return value


def _build_result(case_id: str, findings: list[EvalFinding]) -> EvalResult:
    """根据检查项生成总分。"""
    passed_count = sum(1 for finding in findings if finding.passed)
    score = passed_count / len(findings) if findings else 0
    return EvalResult(
        case_id=case_id,
        passed=all(finding.passed for finding in findings),
        score=round(score, 4),
        findings=findings,
    )

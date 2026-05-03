from dataclasses import dataclass, field
from typing import Any, Literal


WorkflowName = Literal[
    "agent_routing",
    "meeting_to_tasks",
    "maintenance_ticket",
    "quality_issue",
    "purchase_request",
    "weekly_report",
]


@dataclass(frozen=True, slots=True)
class EvalFinding:
    """单条评测发现。"""

    passed: bool
    check_name: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvalResult:
    """单个用例评测结果。"""

    case_id: str
    passed: bool
    score: float
    findings: list[EvalFinding]


@dataclass(frozen=True, slots=True)
class RagEvalCase:
    """知识库问答评测用例。

    企业知识库评测重点不是回答有多华丽，而是是否基于资料、是否带引用、是否避免乱编。
    """

    case_id: str
    question: str
    expected_keywords: tuple[str, ...] = ()
    expected_citation_keywords: tuple[str, ...] = ()
    forbidden_phrases: tuple[str, ...] = ()
    require_citations: bool = True


@dataclass(frozen=True, slots=True)
class WorkflowEvalCase:
    """办公流程与 Agent 路由评测用例。"""

    case_id: str
    workflow_name: WorkflowName
    input_text: str
    expected_intent: str | None = None
    expected_requires_approval: bool | None = None
    expected_workflow_status: str | None = None
    expected_missing_fields: tuple[str, ...] = ()
    expected_output_keywords: tuple[str, ...] = ()
    forbidden_output_keywords: tuple[str, ...] = ()


DEFAULT_RAG_EVAL_CASES: tuple[RagEvalCase, ...] = (
    RagEvalCase(
        case_id="rag_purchase_policy_over_50k",
        question="采购金额超过5万需要谁审批？",
        expected_keywords=("采购", "5万", "审批"),
        expected_citation_keywords=("采购",),
        forbidden_phrases=("我猜", "可能是随便", "无需审批"),
    ),
    RagEvalCase(
        case_id="rag_maintenance_e07_manual",
        question="空压机 E07 报警应该先检查什么？",
        expected_keywords=("空压机", "E07", "检查"),
        expected_citation_keywords=("维修", "空压机"),
        forbidden_phrases=("直接更换整机", "忽略报警"),
    ),
    RagEvalCase(
        case_id="rag_safety_policy",
        question="发现设备漏电时应该如何处理？",
        expected_keywords=("安全", "停机", "上报"),
        expected_citation_keywords=("安全",),
        forbidden_phrases=("继续生产", "不用记录"),
    ),
)


DEFAULT_WORKFLOW_EVAL_CASES: tuple[WorkflowEvalCase, ...] = (
    WorkflowEvalCase(
        case_id="agent_purchase_policy_question",
        workflow_name="agent_routing",
        input_text="采购超过5万需要谁审批？",
        expected_intent="knowledge_qa",
        expected_requires_approval=False,
        expected_output_keywords=("知识库", "不需要审批"),
        forbidden_output_keywords=("采购申请草稿", "提交采购申请"),
    ),
    WorkflowEvalCase(
        case_id="agent_maintenance_question",
        workflow_name="agent_routing",
        input_text="空压机E07报警怎么处理？",
        expected_intent="knowledge_qa",
        expected_requires_approval=False,
        expected_output_keywords=("知识库",),
        forbidden_output_keywords=("维修工单草稿",),
    ),
    WorkflowEvalCase(
        case_id="agent_maintenance_ticket",
        workflow_name="agent_routing",
        input_text="空压机E07报警，生产线A暂停。",
        expected_intent="maintenance_ticket",
        expected_requires_approval=True,
        expected_output_keywords=("维修工单草稿", "人工确认"),
    ),
    WorkflowEvalCase(
        case_id="agent_quality_issue",
        workflow_name="agent_routing",
        input_text="B2批次零件抽检发现3件尺寸超差，请生成质量异常单。",
        expected_intent="quality_issue",
        expected_requires_approval=True,
        expected_output_keywords=("质量异常", "人工确认"),
        forbidden_output_keywords=("维修工单草稿", "直接放行", "直接报废"),
    ),
    WorkflowEvalCase(
        case_id="quality_issue_draft",
        workflow_name="quality_issue",
        input_text="B2批次零件抽检发现3件尺寸超差，影响当前批次出货。",
        expected_requires_approval=True,
        expected_workflow_status="draft_ready",
        expected_output_keywords=("尺寸超差", "隔离", "复测", "授权人员"),
        forbidden_output_keywords=("直接放行", "无需确认"),
    ),
    WorkflowEvalCase(
        case_id="purchase_missing_fields",
        workflow_name="purchase_request",
        input_text="帮我申请采购20个温度传感器，用于产线改造。",
        expected_requires_approval=False,
        expected_workflow_status="needs_clarification",
        expected_missing_fields=("预算", "供应商"),
        expected_output_keywords=("补充", "缺失字段"),
    ),
    WorkflowEvalCase(
        case_id="purchase_ready",
        workflow_name="purchase_request",
        input_text="帮我申请采购20个温度传感器，预算2万元，用于产线改造，供应商为华南传感器。",
        expected_requires_approval=True,
        expected_workflow_status="draft_ready",
        expected_output_keywords=("采购申请草稿", "人工确认"),
    ),
    WorkflowEvalCase(
        case_id="meeting_command_without_content",
        workflow_name="meeting_to_tasks",
        input_text="帮我把这份会议纪要整理成任务。",
        expected_requires_approval=False,
        expected_workflow_status="needs_clarification",
        expected_output_keywords=("补充", "会议纪要正文"),
    ),
    WorkflowEvalCase(
        case_id="meeting_real_tasks",
        workflow_name="meeting_to_tasks",
        input_text="今天会议确定：张工周五前完成设备巡检方案；李工下周一联系供应商确认交期。",
        expected_requires_approval=True,
        expected_workflow_status="draft_ready",
        expected_output_keywords=("张工", "李工", "周五前", "下周一"),
        forbidden_output_keywords=("李工下",),
    ),
)

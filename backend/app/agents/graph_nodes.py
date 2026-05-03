from typing import Any

from app.agents.graph_state import AgentIntent, AuditEvent, FactoryAgentState, ToolCallDraft
from app.agents.slot_filling import build_clarification_question, build_effective_message, fill_slots
from app.agents.sop_registry import match_sop, sop_to_trace_detail
from app.agents.task_state import infer_task_status
from app.agents.trace import append_trace_step
from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.knowledge_service import search_knowledge
from app.workflows.meeting_to_tasks import generate_task_drafts
from app.workflows.purchase_request import generate_purchase_request
from app.workflows.quality_issue import generate_quality_issue_ticket


def classify_intent_node(state: FactoryAgentState) -> FactoryAgentState:
    """意图识别节点。

    当前使用确定性关键词规则，后续可替换为 LLM 分类。
    """
    message = state.get("message", "")
    context = state.get("context", {})
    context_intent = _intent_from_context(context)
    intent = context_intent or classify_intent(message)
    effective_message = build_effective_message(message, context)
    sop = match_sop(intent)
    trace_steps = append_trace_step(
        state.get("trace_steps", []),
        step="classify_intent",
        status="success",
        detail={
            "intent": intent,
            "from_context": context_intent is not None,
        },
    )
    trace_steps = append_trace_step(
        trace_steps,
        step="match_sop",
        status="matched" if sop else "not_matched",
        detail=sop_to_trace_detail(sop),
    )
    return _merge_state(
        state,
        {
            "intent": intent,
            "effective_message": effective_message,
            "sop_id": sop.sop_id if sop else None,
            "sop_name": sop.name if sop else None,
            "trace_steps": trace_steps,
            "audit_events": _append_event(
                state,
                action="classify_intent",
                status="success",
                detail={"intent": intent, "sop_id": sop.sop_id if sop else None},
            ),
        },
    )


def retrieve_knowledge_node(state: FactoryAgentState) -> FactoryAgentState:
    """知识库检索节点。

    有数据库会话时执行真实 RAG 检索；没有数据库会话时保留降级提示。
    """
    db = state.get("db")
    if db is None:
        return _merge_state(
            state,
            {
            "retrieved_chunks": [],
            "trace_steps": append_trace_step(
                state.get("trace_steps", []),
                step="retrieve_knowledge",
                status="skipped",
                detail={"reason": "db_session_missing"},
            ),
            "audit_events": _append_event(
                state,
                action="retrieve_knowledge",
                    status="skipped",
                    detail={"message": "当前 Agent 运行环境未传入数据库会话，已跳过知识库检索。"},
                ),
            },
        )

    response = search_knowledge(
        db,
        KnowledgeSearchRequest(query=state.get("effective_message") or state.get("message", ""), top_k=5),
    )
    retrieved_chunks = [
        {
            "document_id": item.document_id,
            "document_title": item.document_title,
            "filename": item.filename,
            "chunk_id": item.chunk_id,
            "chunk_index": item.chunk_index,
            "chunk_text": item.chunk_text,
            "score": item.score,
        }
        for item in response.results
    ]
    return _merge_state(
        state,
        {
            "retrieved_chunks": retrieved_chunks,
            "trace_steps": append_trace_step(
                state.get("trace_steps", []),
                step="retrieve_knowledge",
                status="success",
                detail={"chunk_count": len(retrieved_chunks)},
            ),
            "audit_events": _append_event(
                state,
                action="retrieve_knowledge",
                status="success",
                detail={"chunk_count": len(retrieved_chunks)},
            ),
        },
    )


def select_tools_node(state: FactoryAgentState) -> FactoryAgentState:
    """工具选择节点，根据意图生成工具调用草稿。"""
    intent = state.get("intent", "unknown")
    sop = match_sop(intent)
    slot_result = fill_slots(sop, state.get("message", ""), state.get("context", {}))
    missing_fields = slot_result.missing_fields

    if sop and missing_fields:
        next_question = build_clarification_question(sop, missing_fields)
        tool_calls = [
            {
                "tool_name": sop.preview_tool_name,
                "tool_args": {
                    "source_text": slot_result.effective_message,
                    "missing_fields": missing_fields,
                    "slot_values": slot_result.slot_values,
                },
                "requires_approval": False,
                "reason": next_question,
            }
        ]
    else:
        next_question = None
        tool_calls = build_tool_calls(intent, slot_result.effective_message)

    requires_approval = any(tool_call.get("requires_approval", False) for tool_call in tool_calls)
    task_status = infer_task_status(
        has_sop=sop is not None,
        missing_fields=missing_fields,
        requires_approval=requires_approval,
        has_tool_calls=bool(tool_calls),
        error=state.get("error"),
    )
    trace_steps = append_trace_step(
        state.get("trace_steps", []),
        step="slot_filling",
        status="needs_clarification" if missing_fields else "complete",
        detail={
            "slot_values": slot_result.slot_values,
            "missing_fields": missing_fields,
        },
    )
    trace_steps = append_trace_step(
        trace_steps,
        step="select_tools",
        status="success",
        detail={
            "tool_count": len(tool_calls),
            "requires_approval": requires_approval,
            "task_status": task_status,
        },
    )

    return _merge_state(
        state,
        {
            "effective_message": slot_result.effective_message,
            "slot_values": slot_result.slot_values,
            "missing_fields": missing_fields,
            "next_question": next_question,
            "task_status": task_status,
            "tool_calls": tool_calls,
            "requires_approval": requires_approval,
            "approval_payload": {
                "intent": intent,
                "sop_id": sop.sop_id if sop else None,
                "task_status": task_status,
                "slot_values": slot_result.slot_values,
                "missing_fields": missing_fields,
                "tool_calls": tool_calls,
            } if requires_approval else {},
            "trace_steps": trace_steps,
            "audit_events": _append_event(
                state,
                action="select_tools",
                status="success",
                detail={
                    "tool_count": len(tool_calls),
                    "requires_approval": requires_approval,
                    "task_status": task_status,
                    "missing_fields": missing_fields,
                },
            ),
        },
    )


def approval_gate_node(state: FactoryAgentState) -> FactoryAgentState:
    """审批判断节点。

    这里不执行工具，只标记是否需要人工确认。
    """
    requires_approval = state.get("requires_approval", False)
    return _merge_state(
        state,
        {
            "trace_steps": append_trace_step(
                state.get("trace_steps", []),
                step="approval_gate",
                status="pending" if requires_approval else "skipped",
                detail={"requires_approval": requires_approval},
            ),
            "audit_events": _append_event(
                state,
                action="approval_gate",
                status="pending" if requires_approval else "skipped",
                detail={"requires_approval": requires_approval},
            )
        },
    )


def final_answer_node(state: FactoryAgentState) -> FactoryAgentState:
    """最终回答节点。"""
    intent = state.get("intent", "unknown")
    requires_approval = state.get("requires_approval", False)
    answer = build_final_answer(
        intent,
        requires_approval,
        state.get("tool_calls", []),
        state.get("retrieved_chunks", []),
        sop_name=state.get("sop_name"),
        task_status=state.get("task_status"),
        missing_fields=state.get("missing_fields", []),
        next_question=state.get("next_question"),
    )
    return _merge_state(
        state,
        {
            "answer": answer,
            "trace_steps": append_trace_step(
                state.get("trace_steps", []),
                step="final_answer",
                status="success",
                detail={"intent": intent, "task_status": state.get("task_status")},
            ),
            "audit_events": _append_event(
                state,
                action="final_answer",
                status="success",
                detail={"intent": intent},
            ),
        },
    )


def classify_intent(message: str) -> AgentIntent:
    """基于关键词识别办公场景。"""
    text = message.lower()

    if _looks_like_knowledge_question(text):
        return "knowledge_qa"
    if _looks_like_meeting_task_request(text):
        return "meeting_to_tasks"
    if _looks_like_purchase_action(text):
        return "purchase_request"
    if _looks_like_quality_issue(text):
        return "quality_issue"
    if _looks_like_maintenance_issue(text):
        return "maintenance_ticket"
    if any(keyword in text for keyword in ["周报", "本周进展", "下周计划", "项目进展"]):
        return "weekly_report"
    return "unknown"


def build_tool_calls(intent: AgentIntent, message: str) -> list[ToolCallDraft]:
    """根据意图生成工具调用草稿。"""
    if intent == "meeting_to_tasks":
        response = generate_task_drafts(message)
        if not response.tasks:
            return [
                {
                    "tool_name": "preview_tasks_from_meeting",
                    "tool_args": {"source_text": message},
                    "requires_approval": False,
                    "reason": "没有识别出明确任务，请补充会议纪要正文、负责人或截止时间。",
                }
            ]
        return [
            {
                "tool_name": "preview_tasks_from_meeting",
                "tool_args": {"source_text": message},
                "requires_approval": True,
                "reason": "先生成任务草稿；真正批量创建任务需要人工确认。",
            }
        ]
    if intent == "maintenance_ticket":
        return [
            {
                "tool_name": "preview_maintenance_ticket",
                "tool_args": {"issue_description": message},
                "requires_approval": True,
                "reason": "先生成维修工单草稿；真正提交维修工单需要人工确认。",
            }
        ]
    if intent == "quality_issue":
        response = generate_quality_issue_ticket(message)
        if response.workflow_status == "needs_clarification":
            return [
                {
                    "tool_name": "preview_quality_issue_ticket",
                    "tool_args": {"issue_description": message},
                    "requires_approval": False,
                    "reason": "质量异常信息不完整，请补充异常现象、批次、产品或检验结果。",
                }
            ]
        return [
            {
                "tool_name": "preview_quality_issue_ticket",
                "tool_args": {"issue_description": message},
                "requires_approval": True,
                "reason": "先生成 NCR/质量异常工单草稿；正式提交需要质量负责人或授权人员确认。",
            }
        ]
    if intent == "purchase_request":
        response = generate_purchase_request(message)
        if response.missing_fields:
            return [
                {
                    "tool_name": "preview_purchase_request",
                    "tool_args": {"purchase_description": message},
                    "requires_approval": False,
                    "reason": f"采购申请信息不完整，请先补充：{'、'.join(response.missing_fields)}。",
                }
            ]
        return [
            {
                "tool_name": "preview_purchase_request",
                "tool_args": {"purchase_description": message},
                "requires_approval": True,
                "reason": "先生成采购申请草稿；真正提交采购申请需要人工确认。",
            }
        ]
    if intent == "knowledge_qa":
        return [
            {
                "tool_name": "search_knowledge_base",
                "tool_args": {"query": message},
                "requires_approval": False,
                "reason": "知识库查询不需要审批。",
            }
        ]
    if intent == "weekly_report":
        return [
            {
                "tool_name": "generate_weekly_report",
                "tool_args": {"source_text": message},
                "requires_approval": False,
                "reason": "生成周报草稿不直接写入业务系统。",
            }
        ]
    return []


def build_final_answer(
    intent: AgentIntent,
    requires_approval: bool,
    tool_calls: list[ToolCallDraft] | None = None,
    retrieved_chunks: list[dict] | None = None,
    *,
    sop_name: str | None = None,
    task_status: str | None = None,
    missing_fields: list[dict] | None = None,
    next_question: str | None = None,
) -> str:
    """根据意图和审批状态生成当前阶段回答。"""
    status_text = f"当前状态：{task_status}。" if task_status else ""
    sop_text = f"命中 SOP：{sop_name}。" if sop_name else ""
    if missing_fields and next_question:
        return f"{sop_text}{status_text}{next_question}"

    if intent == "knowledge_qa" and retrieved_chunks:
        citation_text = "；".join(
            _format_retrieved_chunk_label(chunk)
            for chunk in retrieved_chunks[:3]
        )
        return f"{sop_text}{status_text}已检索到相关企业文档片段，可基于这些来源回答。引用来源：{citation_text}。"

    intent_messages = {
        "knowledge_qa": "已识别为知识库问答请求，但当前没有检索到足够相关的企业文档片段，请先导入或补充对应制度、SOP、设备手册或流程文档。",
        "meeting_to_tasks": "已识别为会议纪要转任务请求，系统会先生成任务草稿。",
        "maintenance_ticket": "已识别为设备维修工单请求，系统会先生成维修工单草稿。",
        "quality_issue": "已识别为质量异常处理请求，系统会先生成 NCR/质量异常工单草稿。",
        "purchase_request": "已识别为采购申请请求，系统会先生成采购申请草稿。",
        "weekly_report": "已识别为项目周报生成请求，系统会生成周报草稿。",
        "unknown": "暂时无法判断该请求所属流程，请补充业务场景或操作目标。",
    }
    if not requires_approval and tool_calls:
        reason = tool_calls[0].get("reason")
        if reason:
            return f"{sop_text}{status_text}{intent_messages[intent]}{reason}"

    suffix = "该动作需要人工确认后才能执行。" if requires_approval else "当前动作不涉及高风险写入。"
    return f"{sop_text}{status_text}{intent_messages[intent]}{suffix}"


def _format_retrieved_chunk_label(chunk: dict) -> str:
    """格式化 Agent 检索来源。"""
    title = chunk.get("document_title") or chunk.get("filename") or "未命名文档"
    chunk_index = chunk.get("chunk_index")
    if chunk_index is None:
        return str(title)
    return f"{title} chunk {chunk_index}"


def _looks_like_knowledge_question(text: str) -> bool:
    """判断是否是制度、流程、手册类咨询，而不是发起业务动作。"""
    policy_keywords = ["制度", "流程", "规范", "规定", "sop", "手册", "谁审批", "怎么审批", "如何审批"]
    question_keywords = ["怎么", "如何", "谁", "是否", "吗", "超过", "多少", "哪些", "什么条件", "怎么办", "怎么处理"]
    if any(keyword in text for keyword in policy_keywords):
        return True
    return any(keyword in text for keyword in question_keywords) and any(
        domain in text for domain in [
            "采购",
            "报销",
            "维修",
            "质量",
            "安全",
            "设备",
            "工单",
            "审批",
            "空压机",
            "注塑机",
            "传感器",
            "报警",
            "故障",
        ]
    )


def _looks_like_meeting_task_request(text: str) -> bool:
    """判断是否是会议纪要转任务请求或真实会议任务内容。"""
    if any(keyword in text for keyword in ["会议纪要", "会议记录", "整理任务", "生成任务"]):
        return True
    task_keywords = ["负责", "完成", "跟进", "确认", "联系", "提交", "输出", "整理", "审批", "检查"]
    return "会议" in text and any(keyword in text for keyword in task_keywords)


def _looks_like_purchase_action(text: str) -> bool:
    """判断是否是采购申请动作。"""
    action_keywords = ["申请采购", "申请购买", "帮我采购", "帮我买", "我要采购", "需要采购", "购买"]
    if any(keyword in text for keyword in action_keywords):
        return True
    return "采购" in text and any(keyword in text for keyword in ["用于", "预算", "供应商", "数量", "个", "台", "套"])


def _looks_like_quality_issue(text: str) -> bool:
    """判断是否是需要生成质量异常处理单的描述。"""
    if any(keyword in text for keyword in ["质量异常报告", "质量异常单", "ncr", "不合格品处理单"]):
        return True
    quality_keywords = ["质量异常", "不合格", "超差", "抽检", "复检", "客诉", "退货", "返工", "报废"]
    product_keywords = ["批次", "零件", "产品", "样件", "来料", "成品", "尺寸", "外观", "检验", "客户"]
    return any(keyword in text for keyword in quality_keywords) and any(
        keyword in text for keyword in product_keywords
    )


def _looks_like_maintenance_issue(text: str) -> bool:
    """判断是否是需要生成维修工单的设备异常描述。"""
    issue_keywords = ["维修", "故障", "报警", "停机", "停线", "停产", "暂停", "异常", "漏电", "冒烟"]
    equipment_keywords = ["空压机", "注塑机", "输送线", "包装机", "传感器", "生产线", "设备"]
    return any(keyword in text for keyword in issue_keywords) and any(
        keyword in text for keyword in equipment_keywords
    )


def _append_event(
    state: FactoryAgentState,
    *,
    action: str,
    status: str,
    detail: dict,
) -> list[AuditEvent]:
    """追加 Agent 内部审计事件。"""
    return [
        *state.get("audit_events", []),
        {
            "action": action,
            "status": status,
            "detail": detail,
        },
    ]


def _intent_from_context(context: dict[str, Any]) -> AgentIntent | None:
    """从多轮上下文中恢复正在补槽的业务意图。"""
    status = context.get("task_status")
    intent = context.get("active_intent") or context.get("intent")
    valid_intents = {
        "knowledge_qa",
        "meeting_to_tasks",
        "maintenance_ticket",
        "quality_issue",
        "purchase_request",
        "weekly_report",
        "unknown",
    }
    if status == "collecting_info" and intent in valid_intents:
        return intent
    return None


def _merge_state(state: FactoryAgentState, patch: FactoryAgentState) -> FactoryAgentState:
    """合并节点输出。"""
    return {**state, **patch}

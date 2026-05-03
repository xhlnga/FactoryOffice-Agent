import re

from app.models.base import TaskPriority
from app.schemas.workflow import QualityIssueResponse, QualityIssueTicketDraft


def generate_quality_issue_ticket(issue_description: str) -> QualityIssueResponse:
    """根据质量异常描述生成 NCR/质量异常工单草稿。

    质量异常通常需要隔离、复检、原因分析和责任部门确认。这里只生成草稿，
    不直接判定最终责任，也不直接放行、返工或报废产品。
    """
    cleaned = issue_description.strip()
    if not _has_quality_signal(cleaned):
        return QualityIssueResponse(
            source=issue_description,
            quality_issue_draft=None,
            workflow_status="needs_clarification",
            requires_approval=False,
            message="未识别到明确质量异常，请补充异常现象、批次、产品或检验结果。",
        )

    draft = QualityIssueTicketDraft(
        ticket_type="质量异常",
        title=_build_quality_title(cleaned),
        description=cleaned,
        priority=_infer_quality_priority(cleaned),
        abnormality_type=_infer_abnormality_type(cleaned),
        affected_scope=_infer_affected_scope(cleaned),
        initial_disposition=_build_initial_disposition(cleaned),
        required_actions=_build_required_actions(cleaned),
    )
    return QualityIssueResponse(
        source=issue_description,
        quality_issue_draft=draft,
        workflow_status="draft_ready",
        requires_approval=True,
        message="已生成质量异常工单草稿，正式提交前需要质量负责人或授权人员确认。",
    )


def _has_quality_signal(text: str) -> bool:
    """判断输入是否包含质量异常信号。"""
    quality_keywords = [
        "质量异常",
        "不合格",
        "超差",
        "尺寸",
        "抽检",
        "复检",
        "客诉",
        "退货",
        "报废",
        "返工",
        "批次",
        "来料",
        "首检",
        "巡检",
        "终检",
        "ncr",
    ]
    return any(keyword in text.lower() for keyword in quality_keywords)


def _build_quality_title(text: str) -> str:
    """生成质量异常工单标题。"""
    batch = _extract_batch(text)
    abnormality_type = _infer_abnormality_type(text)
    if batch:
        return f"{batch}{abnormality_type}质量异常"
    return f"{abnormality_type}质量异常处理"


def _infer_abnormality_type(text: str) -> str:
    """推断异常类型，保持可解释而不是臆断根因。"""
    if any(keyword in text for keyword in ["尺寸", "公差", "超差", "孔径", "厚度", "长度", "宽度"]):
        return "尺寸超差"
    if any(keyword in text for keyword in ["外观", "划伤", "磕碰", "毛刺", "色差", "变形"]):
        return "外观不良"
    if any(keyword in text for keyword in ["来料", "供应商", "入厂", "原材料"]):
        return "来料异常"
    if any(keyword in text for keyword in ["客诉", "客户", "退货", "售后"]):
        return "客户反馈异常"
    if any(keyword in text for keyword in ["性能", "压力", "温度", "泄漏", "密封"]):
        return "性能异常"
    return "一般质量异常"


def _infer_quality_priority(text: str) -> TaskPriority:
    """根据影响范围和客户影响推断质量异常优先级。"""
    if any(keyword in text for keyword in ["停线", "停产", "客户停线", "批量", "客诉", "退货", "安全风险"]):
        return TaskPriority.URGENT
    if any(keyword in text for keyword in ["抽检", "超差", "不合格", "隔离", "返工", "报废"]):
        return TaskPriority.HIGH
    return TaskPriority.MEDIUM


def _infer_affected_scope(text: str) -> str:
    """提取或推断影响范围。"""
    batch = _extract_batch(text)
    if batch:
        return batch
    match = re.search(r"(本批次|该批次|当前批次|[\d一二三四五六七八九十]+件|[\d一二三四五六七八九十]+批)", text)
    if match:
        return match.group(0)
    if any(keyword in text for keyword in ["客户", "客诉", "退货"]):
        return "客户反馈相关批次"
    return "待质量人员确认影响批次和数量"


def _build_initial_disposition(text: str) -> str:
    """生成初步处置建议，避免越权做最终处理决定。"""
    actions = ["隔离疑似异常物料或成品", "暂停放行相关批次", "保留检验记录和样件"]
    if any(keyword in text for keyword in ["尺寸", "超差", "抽检", "复检"]):
        actions.append("安排质量人员复测关键尺寸并记录检测设备编号")
    if any(keyword in text for keyword in ["来料", "供应商"]):
        actions.append("通知采购或供应商质量工程师参与确认")
    if any(keyword in text for keyword in ["客户", "客诉", "退货"]):
        actions.append("同步销售或项目负责人，确认客户影响范围")
    return "；".join(actions)


def _build_required_actions(text: str) -> list[str]:
    """列出质量异常单需要推进的后续动作。"""
    actions = [
        "质量人员确认异常事实和影响范围",
        "责任部门提交初步原因分析",
        "评估返工、让步接收、报废或退供应商等处置方案",
        "处置方案经授权人员确认后执行",
        "关闭前补充纠正预防措施和复验记录",
    ]
    if any(keyword in text for keyword in ["客户", "客诉", "退货"]):
        actions.insert(2, "必要时启动客户问题 8D 分析")
    return actions


def _extract_batch(text: str) -> str | None:
    """抽取批次信息。"""
    match = re.search(r"([A-Za-z0-9_-]{2,20}批次|批次[A-Za-z0-9_-]{2,20}|[A-Za-z]\d{1,4}批)", text)
    return match.group(0) if match else None

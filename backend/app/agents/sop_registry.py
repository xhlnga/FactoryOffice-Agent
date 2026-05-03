from app.workflows.sop_definitions import SOPDefinition, get_sop_definition


def match_sop(intent: str | None) -> SOPDefinition | None:
    """根据意图匹配企业 SOP。

    这里保持单意图单 SOP，后续如果出现多业务线，可替换为配置表或数据库驱动。
    """
    return get_sop_definition(intent)


def sop_to_trace_detail(sop: SOPDefinition | None) -> dict:
    """把 SOP 摘要转换为 Trace 可展示字段。"""
    if sop is None:
        return {"sop_id": None, "sop_name": None}
    return {
        "sop_id": sop.sop_id,
        "sop_name": sop.name,
        "approval_policy": sop.approval_policy,
        "preview_tool_name": sop.preview_tool_name,
        "execution_target": sop.execution_target,
    }


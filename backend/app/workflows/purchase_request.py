import re

from app.schemas.workflow import PurchaseDraft, PurchaseWorkflowResponse


REQUIRED_FIELDS = {
    "item_name": "物品名称",
    "quantity": "数量",
    "reason": "采购原因",
    "budget": "预算",
    "supplier": "供应商",
}


def generate_purchase_request(requirement: str) -> PurchaseWorkflowResponse:
    """根据采购需求生成采购申请草稿。"""
    if _looks_like_purchase_policy_question(requirement):
        return PurchaseWorkflowResponse(
            source=requirement,
            purchase_draft=PurchaseDraft(),
            missing_fields=["采购物品", "数量", "采购原因", "预算", "供应商"],
            workflow_status="needs_clarification",
            requires_approval=False,
            message="该输入更像采购制度或审批规则咨询，不应直接生成采购申请草稿；请在知识库问答中查询制度依据。",
        )

    draft = PurchaseDraft(
        item_name=extract_item_name(requirement),
        quantity=extract_quantity(requirement),
        reason=extract_reason(requirement),
        budget=extract_budget(requirement),
        supplier=extract_supplier(requirement),
    )
    missing_fields = find_missing_fields(draft)
    if missing_fields:
        return PurchaseWorkflowResponse(
            source=requirement,
            purchase_draft=draft,
            missing_fields=missing_fields,
            workflow_status="needs_clarification",
            requires_approval=False,
            message="采购申请草稿信息不完整，请先补充缺失字段，再进入人工确认。",
        )

    return PurchaseWorkflowResponse(
        source=requirement,
        purchase_draft=draft,
        missing_fields=missing_fields,
        workflow_status="draft_ready",
        requires_approval=True,
        message="已生成采购申请草稿，提交采购前需要人工确认。",
    )


def extract_item_name(text: str) -> str | None:
    """抽取物品名称。"""
    patterns = [
        r"采购\s*\d*\s*个?\s*(?P<item>[\u4e00-\u9fffA-Za-z0-9_-]{2,30})",
        r"购买\s*\d*\s*个?\s*(?P<item>[\u4e00-\u9fffA-Za-z0-9_-]{2,30})",
        r"申请\s*采购\s*\d*\s*个?\s*(?P<item>[\u4e00-\u9fffA-Za-z0-9_-]{2,30})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group("item").strip("，,。.")
    return None


def extract_quantity(text: str) -> int | None:
    """抽取数量。"""
    match = re.search(r"(?P<quantity>\d+)\s*(个|台|套|件|箱|批|支|只|根|卷|包)", text)
    return int(match.group("quantity")) if match else None


def extract_reason(text: str) -> str | None:
    """抽取采购原因。"""
    match = re.search(r"(用于|因为|原因是|为)\s*(?P<reason>[^，。；;]+)", text)
    if match:
        return match.group("reason").strip()
    return None


def extract_budget(text: str) -> float | None:
    """抽取预算金额。"""
    match = re.search(r"(预算|金额|费用)[^\d]*(?P<budget>\d+(?:\.\d+)?)\s*(?P<unit>万元|万|元)?", text)
    if not match:
        return None
    amount = float(match.group("budget"))
    unit = match.group("unit")
    if unit in {"万", "万元"}:
        return amount * 10000
    return amount


def extract_supplier(text: str) -> str | None:
    """抽取供应商。"""
    match = re.search(r"(供应商|厂家|供货方)[为是:：]?\s*(?P<supplier>[\u4e00-\u9fffA-Za-z0-9_-]{2,50})", text)
    if match:
        return match.group("supplier")
    return None


def find_missing_fields(draft: PurchaseDraft) -> list[str]:
    """检查采购申请草稿缺失字段。"""
    data = draft.model_dump()
    return [label for field, label in REQUIRED_FIELDS.items() if data.get(field) in {None, ""}]


def _looks_like_purchase_policy_question(text: str) -> bool:
    """识别采购制度咨询，避免把“超过 5 万怎么审批”误当采购申请。"""
    return "采购" in text and any(keyword in text for keyword in ["怎么审批", "如何审批", "谁审批", "审批流程"])

from app.schemas.workflow import WeeklyReportDraft, WeeklyReportResponse


def generate_weekly_report(source_text: str) -> WeeklyReportResponse:
    """根据项目记录生成周报草稿。"""
    report = WeeklyReportDraft(
        progress=extract_section(source_text, ["完成", "进展", "上线", "交付"]) or "本周进展待补充。",
        issues=extract_section(source_text, ["问题", "阻塞", "延期", "异常"]) or "本周问题待补充。",
        quality_risks=extract_section(source_text, ["质量", "返工", "不良", "异常"]) or "暂无明确质量风险。",
        equipment_risks=extract_section(source_text, ["设备", "停机", "维修", "报警"]) or "暂无明确设备风险。",
        purchase_risks=extract_section(source_text, ["采购", "供应商", "交期", "物料"]) or "暂无明确采购风险。",
        next_plan=extract_section(source_text, ["下周", "计划", "推进", "跟进"]) or "下周计划待补充。",
        decisions_needed=extract_section(source_text, ["决策", "审批", "协调", "支持"]) or "暂无明确需要管理层决策事项。",
    )
    return WeeklyReportResponse(
        source=source_text,
        weekly_report=report,
        message="已生成项目周报草稿，请人工复核后使用。",
    )


def extract_section(text: str, keywords: list[str]) -> str | None:
    """从原始记录中抽取包含关键词的句子。"""
    sentences = [part.strip() for part in text.replace("\n", "。").split("。") if part.strip()]
    matched = [
        sentence
        for sentence in sentences
        if any(keyword in sentence for keyword in keywords)
    ]
    return "；".join(matched[:3]) if matched else None


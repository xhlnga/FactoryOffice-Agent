from fastapi import APIRouter

from app.schemas.workflow import (
    MaintenanceTicketResponse,
    MeetingToTasksResponse,
    PurchaseWorkflowResponse,
    QualityIssueResponse,
    TextWorkflowRequest,
    WeeklyReportResponse,
)
from app.workflows.maintenance_ticket import generate_maintenance_ticket
from app.workflows.meeting_to_tasks import generate_task_drafts
from app.workflows.purchase_request import generate_purchase_request
from app.workflows.quality_issue import generate_quality_issue_ticket
from app.workflows.weekly_report import generate_weekly_report

router = APIRouter()


@router.post("/meeting-to-tasks", response_model=MeetingToTasksResponse, summary="会议纪要转任务")
def meeting_to_tasks(request: TextWorkflowRequest) -> MeetingToTasksResponse:
    """从会议纪要中提取任务草稿，后续进入人工确认。"""
    return generate_task_drafts(request.content)


@router.post("/maintenance-ticket", response_model=MaintenanceTicketResponse, summary="设备异常转维修工单")
def maintenance_ticket(request: TextWorkflowRequest) -> MaintenanceTicketResponse:
    """根据设备异常描述生成维修工单草稿。"""
    return generate_maintenance_ticket(request.content)


@router.post("/quality-issue", response_model=QualityIssueResponse, summary="质量异常转处理工单")
def quality_issue(request: TextWorkflowRequest) -> QualityIssueResponse:
    """根据质量异常描述生成 NCR/质量异常工单草稿。"""
    return generate_quality_issue_ticket(request.content)


@router.post("/purchase-request", response_model=PurchaseWorkflowResponse, summary="采购需求转申请草稿")
def purchase_request(request: TextWorkflowRequest) -> PurchaseWorkflowResponse:
    """根据采购需求生成采购申请草稿，必要时提示补充字段。"""
    return generate_purchase_request(request.content)


@router.post("/weekly-report", response_model=WeeklyReportResponse, summary="生成项目周报")
def weekly_report(request: TextWorkflowRequest) -> WeeklyReportResponse:
    """根据项目记录生成周报草稿。"""
    return generate_weekly_report(request.content)

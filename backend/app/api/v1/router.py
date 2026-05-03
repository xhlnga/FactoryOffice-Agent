from fastapi import APIRouter

from app.api.v1.endpoints import (
    agent,
    approvals,
    audit_logs,
    auth,
    documents,
    health,
    knowledge,
    purchases,
    tasks,
    tickets,
    workflows,
)


api_router = APIRouter()

# 所有 v1 endpoints 在这里统一注册，保持入口清晰。
api_router.include_router(health.router, tags=["健康检查"])
api_router.include_router(auth.router, prefix="/auth", tags=["身份模拟"])
api_router.include_router(documents.router, prefix="/documents", tags=["文档管理"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["办公流程"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["工单"])
api_router.include_router(purchases.router, prefix="/purchases", tags=["采购申请"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["审批"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["审计日志"])

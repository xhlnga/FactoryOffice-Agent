from sqlalchemy.orm import Session

from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.knowledge_service import search_knowledge
from app.tools.base import AgentTool, RiskLevel, ToolResult


def search_knowledge_base(db: Session, query: str, top_k: int = 5) -> ToolResult:
    """搜索企业知识库。"""
    response = search_knowledge(db, KnowledgeSearchRequest(query=query, top_k=top_k))
    return ToolResult(
        tool_name="search_knowledge_base",
        success=True,
        message=response.message,
        data=response.model_dump(),
        requires_approval=False,
    )


SEARCH_KNOWLEDGE_BASE_TOOL = AgentTool(
    name="search_knowledge_base",
    description="搜索企业制度、SOP、设备手册、质量流程和安全规范。",
    handler=search_knowledge_base,
    requires_approval=False,
    risk_level=RiskLevel.LOW,
)

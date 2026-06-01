from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser, get_current_user_optional
from app.core.database import get_db
from app.schemas.knowledge import KnowledgeAskRequest, KnowledgeSearchRequest
from app.services.knowledge_service import ask_knowledge as ask_knowledge_service
from app.services.knowledge_service import search_knowledge as search_knowledge_service
from app.services.permission_service import build_document_access_context

router = APIRouter()


@router.post("/search", summary="知识库检索")
def search_knowledge(
    request: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[AuthenticatedUser | None, Depends(get_current_user_optional)] = None,
) -> dict:
    """根据用户问题检索相关文档片段。"""
    auth_context = build_document_access_context(db, current_user)
    return search_knowledge_service(db, request, auth_context=auth_context).model_dump(mode="json")


@router.post("/ask", summary="知识库问答")
def ask_knowledge(
    request: KnowledgeAskRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[AuthenticatedUser | None, Depends(get_current_user_optional)] = None,
) -> dict:
    """基于检索结果生成回答，回答必须尽量包含引用来源。"""
    auth_context = build_document_access_context(db, current_user)
    return ask_knowledge_service(db, request, auth_context=auth_context).model_dump(mode="json")

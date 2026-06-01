from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser, get_current_user_optional
from app.core.database import get_db
from app.core.security import UserRole, require_role
from app.schemas.approval import ApprovalCreateRequest
from app.schemas.document import DocumentRead
from app.services.approval_service import create_approval
from app.services.document_service import get_document
from app.services.document_service import index_document_for_knowledge_base
from app.services.document_service import list_documents as list_document_records
from app.services.document_service import save_upload_and_create_document
from app.services.permission_service import build_document_access_context
from app.utils.file_utils import unlink_if_exists

router = APIRouter()


@router.get("", summary="获取文档列表")
def list_documents(
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="返回数量上限")] = 20,
    db: Session = Depends(get_db),
    current_user: Annotated[AuthenticatedUser | None, Depends(get_current_user_optional)] = None,
) -> dict:
    """查询未删除的知识库文档。"""
    auth_context = build_document_access_context(db, current_user)
    items, total = list_document_records(db, offset=offset, limit=limit, auth_context=auth_context)
    return {
        "items": [DocumentRead.model_validate(item).model_dump(mode="json") for item in items],
        "total": total,
        "message": "文档列表查询成功。",
    }


@router.post("/upload", summary="上传企业文档")
async def upload_document(
    file: UploadFile = File(...),
    category: Annotated[str, Query(min_length=1, max_length=64, description="文档分类")] = "未分类",
    db: Session = Depends(get_db),
    current_user: Annotated[AuthenticatedUser | None, Depends(get_current_user_optional)] = None,
) -> dict:
    """上传文件、创建文档记录，并同步完成知识库切块入库。"""
    auth_context = build_document_access_context(db, current_user)
    document = await save_upload_and_create_document(db, file, category=category, auth_context=auth_context)
    try:
        chunk_count = index_document_for_knowledge_base(db, document)
    except Exception:
        db.rollback()
        if document.file_path:
            unlink_if_exists(Path(document.file_path))
        db.delete(document)
        db.commit()
        raise
    return {
        "document": DocumentRead.model_validate(document).model_dump(mode="json"),
        "status": "indexed",
        "chunk_count": chunk_count,
        "message": f"文件已保存并完成知识库入库，共生成 {chunk_count} 个切块。",
    }


@router.delete("/{document_id}", summary="删除文档")
def request_delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _role: UserRole = Depends(require_role(UserRole.MANAGER)),
    current_user: Annotated[AuthenticatedUser | None, Depends(get_current_user_optional)] = None,
) -> dict:
    """提交删除文档审批；审批通过后才会软删除。"""
    auth_context = build_document_access_context(db, current_user)
    get_document(db, document_id, auth_context=auth_context)
    approval = create_approval(
        db,
        ApprovalCreateRequest(
            action_type="delete_document",
            action_payload={"document_id": document_id},
        ),
    )
    return {
        "document_id": document_id,
        "approval_id": approval.id,
        "status": approval.status,
        "message": "删除文档属于高风险动作，已创建待审批记录。",
    }

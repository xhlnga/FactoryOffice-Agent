from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.base import utc_now
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.document_loader import load_document_text
from app.rag.embedding_client import embed_texts
from app.rag.text_splitter import split_text
from app.rag.vector_store import create_document_chunks
from app.schemas.document import DocumentCreate
from app.services.approval_guard import ensure_approved_action
from app.services.permission_service import (
    DocumentAccessContext,
    can_access_document,
    create_default_document_permissions,
    ensure_document_access,
)
from app.utils.file_utils import (
    file_suffix,
    new_sha256_digest,
    safe_filename,
    unlink_if_exists,
    validate_file_extension,
)
from app.utils.id_utils import uuid_hex


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


@dataclass(frozen=True, slots=True)
class SavedUploadFile:
    """上传文件保存结果。"""

    path: Path
    size_bytes: int
    sha256: str


def _safe_filename(filename: str | None) -> str:
    """清理上传文件名，避免路径穿越。"""
    try:
        return safe_filename(filename)
    except ValueError as exc:
        raise AppException(str(exc), status_code=status.HTTP_400_BAD_REQUEST) from exc


def validate_document_filename(filename: str | None) -> str:
    """校验文档扩展名。"""
    try:
        return validate_file_extension(filename, ALLOWED_EXTENSIONS)
    except ValueError as exc:
        raise AppException(
            "暂不支持该文件类型。",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"allowed_extensions": sorted(ALLOWED_EXTENSIONS)},
        ) from exc


async def save_upload_file(file: UploadFile) -> SavedUploadFile:
    """分块保存上传文件，避免大文件一次性进入内存。"""
    filename = validate_document_filename(file.filename)
    settings.ensure_runtime_dirs()

    suffix = file_suffix(filename)
    stored_name = f"{uuid_hex()}{suffix}"
    target_path = settings.upload_dir / stored_name

    digest = new_sha256_digest()
    size_bytes = 0

    with target_path.open("wb") as output:
        while chunk := await file.read(settings.upload_chunk_size_bytes):
            size_bytes += len(chunk)
            if size_bytes > settings.upload_max_size_bytes:
                output.close()
                unlink_if_exists(target_path)
                raise AppException(
                    "上传文件超过大小限制。",
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    details={"max_size_mb": settings.upload_max_size_mb},
                )
            digest.update(chunk)
            output.write(chunk)

    if size_bytes == 0:
        unlink_if_exists(target_path)
        raise AppException("上传文件内容不能为空。", status_code=status.HTTP_400_BAD_REQUEST)

    return SavedUploadFile(path=target_path, size_bytes=size_bytes, sha256=digest.hexdigest())


def create_document(db: Session, data: DocumentCreate) -> Document:
    """创建文档记录。"""
    document = Document(**data.model_dump())
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


async def save_upload_and_create_document(
    db: Session,
    file: UploadFile,
    *,
    category: str = "未分类",
    uploaded_by: int | None = None,
    auth_context: DocumentAccessContext | None = None,
) -> Document:
    """保存上传文件并创建文档记录。"""
    saved_file = await save_upload_file(file)
    existing_document = get_document_by_sha256(db, saved_file.sha256)
    if existing_document is not None:
        unlink_if_exists(saved_file.path)
        raise AppException(
            "相同内容的文档已存在，已拒绝重复上传。",
            status_code=status.HTTP_409_CONFLICT,
            details={"document_id": existing_document.id, "filename": existing_document.filename},
        )

    filename = _safe_filename(file.filename)
    document_data = DocumentCreate(
        filename=filename,
        title=Path(filename).stem,
        category=category,
        file_path=str(saved_file.path),
        content_type=file.content_type,
        file_size_bytes=saved_file.size_bytes,
        file_sha256=saved_file.sha256,
        uploaded_by=uploaded_by if uploaded_by is not None else (auth_context.user_id if auth_context else None),
    )
    try:
        document = create_document(db, document_data)
        create_default_document_permissions(db, document, auth_context, commit=True)
        return document
    except Exception:
        unlink_if_exists(saved_file.path)
        raise


def list_documents(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 20,
    auth_context: DocumentAccessContext | None = None,
) -> tuple[list[Document], int]:
    """分页查询未删除文档列表。"""
    active_filter = Document.deleted_at.is_(None)
    if auth_context is None:
        total = db.scalar(select(func.count()).select_from(Document).where(active_filter)) or 0
        items = db.scalars(
            select(Document)
            .where(active_filter)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return list(items), total

    # 文档列表通常不会很大；这里先保守过滤，避免不同数据库方言下权限 SQL 差异影响演示。
    all_items = list(db.scalars(select(Document).where(active_filter).order_by(Document.created_at.desc())).all())
    visible_items = [item for item in all_items if can_access_document(db, item, auth_context)]
    return visible_items[offset: offset + limit], len(visible_items)


def get_document(
    db: Session,
    document_id: int,
    *,
    include_deleted: bool = False,
    auth_context: DocumentAccessContext | None = None,
) -> Document:
    """查询文档详情，不存在时抛出业务异常。"""
    document = db.get(Document, document_id)
    if document is None or (document.deleted_at is not None and not include_deleted):
        raise AppException("文档不存在。", status_code=status.HTTP_404_NOT_FOUND)
    ensure_document_access(db, document, auth_context)
    return document


def get_document_by_sha256(db: Session, file_sha256: str) -> Document | None:
    """根据文件摘要查询未删除文档，用于重复上传判断。"""
    return db.scalar(
        select(Document)
        .where(Document.file_sha256 == file_sha256)
        .where(Document.deleted_at.is_(None))
        .limit(1)
    )


def index_document_for_knowledge_base(db: Session, document: Document) -> int:
    """解析文档、切块、生成向量并写入知识库。

    上传文档后同步完成入库，保证前端上传后可以直接用于知识库检索。
    重新索引时先删除旧切块，避免重复检索到同一份文档。
    """
    if not document.file_path:
        raise AppException("文档缺少文件路径，无法入库。", status_code=status.HTTP_400_BAD_REQUEST)

    text = load_document_text(document.file_path)
    chunks = split_text(
        text,
        metadata={
            "document_id": document.id,
            "filename": document.filename,
            "title": document.title,
            "category": document.category,
        },
    )
    if not chunks:
        raise AppException("文档没有可入库的文本内容。", status_code=status.HTTP_400_BAD_REQUEST)

    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    embeddings = embed_texts([chunk.text for chunk in chunks])
    create_document_chunks(db, document_id=document.id, chunks=chunks, embeddings=embeddings)
    return len(chunks)


def delete_document(
    db: Session,
    document_id: int,
    *,
    approved_action: bool = False,
    commit: bool = True,
) -> None:
    """软删除文档记录；保留切块和审计线索，避免企业资料不可追溯。"""
    ensure_approved_action("删除知识库文档", approved_action)
    document = get_document(db, document_id)
    document.deleted_at = utc_now()
    if commit:
        db.commit()
    else:
        db.flush()

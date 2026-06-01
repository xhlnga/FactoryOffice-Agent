from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.rag.text_splitter import TextChunk
from app.services.permission_service import DocumentAccessContext, build_document_permission_sql, table_exists


@dataclass(slots=True)
class VectorSearchResult:
    """向量检索结果。"""

    chunk_id: int
    document_id: int
    chunk_text: str
    chunk_index: int
    score: float | None = None
    filename: str | None = None
    document_title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def create_document_chunks(
    db: Session,
    *,
    document_id: int,
    chunks: list[TextChunk],
    embeddings: list[list[float]] | None = None,
) -> list[DocumentChunk]:
    """保存文档切块和可选向量。"""
    if embeddings is not None and len(embeddings) != len(chunks):
        raise ValueError("embeddings 数量必须与 chunks 数量一致")

    records: list[DocumentChunk] = []
    for index, chunk in enumerate(chunks):
        records.append(
            DocumentChunk(
                document_id=document_id,
                chunk_text=chunk.text,
                chunk_index=chunk.index,
                embedding=embeddings[index] if embeddings is not None else None,
                chunk_metadata=chunk.metadata,
            )
        )

    db.add_all(records)
    db.commit()
    for record in records:
        db.refresh(record)
    return records


def search_similar_chunks(
    db: Session,
    *,
    query_embedding: list[float],
    top_k: int = 5,
    auth_context: DocumentAccessContext | None = None,
) -> list[VectorSearchResult]:
    """基于 pgvector 余弦距离检索相似切块。"""
    vector_literal = _to_vector_literal(query_embedding)
    permission_sql = ""
    permission_params: dict[str, Any] = {}
    if auth_context is not None and table_exists(db, "document_permissions"):
        permission_sql, permission_params = build_document_permission_sql(auth_context)

    rows = db.execute(
        text(
            f"""
            SELECT
                dc.id AS chunk_id,
                dc.document_id AS document_id,
                dc.chunk_text AS chunk_text,
                dc.chunk_index AS chunk_index,
                dc.chunk_metadata AS metadata,
                d.filename AS filename,
                d.title AS document_title,
                1 - (dc.embedding <=> CAST(:query_embedding AS vector)) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.embedding IS NOT NULL
              AND d.deleted_at IS NULL
              {permission_sql}
            ORDER BY dc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
            """
        ),
        {"query_embedding": vector_literal, "top_k": top_k, **permission_params},
    ).mappings()

    return [
        VectorSearchResult(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            chunk_text=row["chunk_text"],
            chunk_index=row["chunk_index"],
            score=float(row["score"]) if row["score"] is not None else None,
            filename=row["filename"],
            document_title=row["document_title"],
            metadata=row["metadata"] or {},
        )
        for row in rows
    ]


def _to_vector_literal(values: list[float]) -> str:
    """把 Python 向量转换为 pgvector 可识别的字面量。"""
    return "[" + ",".join(str(float(value)) for value in values) + "]"

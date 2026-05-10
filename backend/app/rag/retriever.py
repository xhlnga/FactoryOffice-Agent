from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.rag.embedding_client import embed_text
from app.rag.vector_store import VectorSearchResult, search_similar_chunks
from app.retrieval.bm25_index import BM25Index
from app.retrieval.fusion import fuse_results

_bm25_index: BM25Index | None = None


def get_bm25_index() -> BM25Index:
    global _bm25_index
    if _bm25_index is None:
        _bm25_index = BM25Index()
    return _bm25_index


def init_bm25_index(db: Session) -> None:
    from app.models.document_chunk import DocumentChunk
    chunks = db.query(DocumentChunk).all()
    get_bm25_index().build(chunks)


def retrieve_relevant_chunks(
    db: Session,
    *,
    query: str,
    top_k: int = 5,
) -> list[VectorSearchResult]:
    query_embedding = embed_text(query)
    vector_results = search_similar_chunks(
        db, query_embedding=query_embedding, top_k=15
    )
    bm25_results = get_bm25_index().search(query, top_k=15)
    fused = fuse_results(
        vector_results,
        bm25_results,
        alpha=settings.fusion_alpha,
        query=query,
    )
    return fused[:top_k]

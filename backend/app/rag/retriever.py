from sqlalchemy.orm import Session

from app.rag.embedding_client import embed_text
from app.rag.reranker import filter_by_keyword_overlap, rerank_by_keyword_overlap
from app.rag.vector_store import VectorSearchResult, search_similar_chunks
from app.services.permission_service import DocumentAccessContext


def retrieve_relevant_chunks(
    db: Session,
    *,
    query: str,
    top_k: int = 5,
    auth_context: DocumentAccessContext | None = None,
) -> list[VectorSearchResult]:
    """根据用户问题检索相关文档切块。"""
    query_embedding = embed_text(query)
    results = search_similar_chunks(
        db,
        query_embedding=query_embedding,
        top_k=top_k,
        auth_context=auth_context,
    )
    ranked_results = rerank_by_keyword_overlap(query, results)
    return filter_by_keyword_overlap(query, ranked_results)

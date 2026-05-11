from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.rag.prompt_builder import build_citation_label, build_rag_messages
from app.rag.retriever import retrieve_relevant_chunks
from app.rag.vector_store import VectorSearchResult
from app.schemas.knowledge import Citation, KnowledgeAskRequest, KnowledgeAskResponse, KnowledgeSearchRequest, KnowledgeSearchResponse
from app.schemas.knowledge import KnowledgeSearchResult
from app.services.llm_service import chat_completion


def search_knowledge(db: Session, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    """知识库检索入口。"""
    results = retrieve_relevant_chunks(
        db, query=request.query, top_k=request.top_k,
        bm25_query=request.bm25_query,
    )
    return KnowledgeSearchResponse(
        query=request.query,
        top_k=request.top_k,
        results=[_to_search_result(result) for result in results],
        message="知识库检索完成。" if results else "未检索到相关文档片段，请先导入知识库文档。",
    )


def ask_knowledge(db: Session, request: KnowledgeAskRequest) -> KnowledgeAskResponse:
    """知识库问答入口。"""
    results = retrieve_relevant_chunks(db, query=request.question, top_k=request.top_k)
    if not results:
        return KnowledgeAskResponse(
            question=request.question,
            answer="当前知识库资料不足以确认。请先导入相关制度、SOP、设备手册或流程文档。",
            citations=[],
            message="未检索到相关文档片段。",
        )

    citations = [_to_citation(result) for result in results]
    answer = _generate_answer(question=request.question, results=results)
    return KnowledgeAskResponse(
        question=request.question,
        answer=answer,
        citations=citations,
        message="知识库问答完成。",
    )


def _generate_answer(*, question: str, results: list[VectorSearchResult]) -> str:
    """生成回答；没有可用 LLM 时使用抽取式兜底回答。"""
    if _has_real_llm_config():
        try:
            return chat_completion(build_rag_messages(question=question, results=results))
        except AppException as exc:
            return _build_extractive_answer(
                question=question,
                results=results,
                note=f"大模型调用失败，已返回基于检索片段的兜底回答：{exc.message}",
            )

    return _build_extractive_answer(
        question=question,
        results=results,
        note="当前未配置真实大模型，已返回基于检索片段的本地兜底回答。",
    )


def _build_extractive_answer(*, question: str, results: list[VectorSearchResult], note: str) -> str:
    """基于检索片段生成可审计的兜底回答。"""
    snippets = []
    for index, result in enumerate(results[:3], start=1):
        text = result.chunk_text.strip().replace("\n", " ")
        if len(text) > 260:
            text = text[:260].rstrip() + "..."
        snippets.append(f"{index}. {text}")

    citations = "\n".join(f"- {build_citation_label(result)}" for result in results)
    return "\n".join(
        [
            note,
            "",
            f"问题：{question}",
            "",
            "根据当前检索到的企业知识库片段，可参考以下内容：",
            *snippets,
            "",
            "涉及正式业务动作、安全风险、质量风险、客户交付或预算事项时，应由对应责任部门人工确认后再执行。",
            "",
            "引用来源：",
            citations,
        ]
    )


def _to_search_result(result: VectorSearchResult) -> KnowledgeSearchResult:
    """向 API 响应转换检索结果。"""
    return KnowledgeSearchResult(
        **_citation_kwargs(result),
        chunk_text=result.chunk_text,
    )


def _to_citation(result: VectorSearchResult) -> Citation:
    """向 API 响应转换引用来源。"""
    return Citation(**_citation_kwargs(result))


def _citation_kwargs(result: VectorSearchResult) -> dict:
    """提取引用字段。"""
    return {
        "document_id": result.document_id,
        "document_title": result.document_title,
        "filename": result.filename,
        "chunk_id": result.chunk_id,
        "chunk_index": result.chunk_index,
        "score": result.score,
    }


def _has_real_llm_config() -> bool:
    """判断是否具备真实 LLM 配置。"""
    if not settings.llm_base_url or not settings.llm_api_key:
        return False
    placeholders = {"your_api_key_here", "changeme", "placeholder"}
    return settings.llm_api_key.strip().lower() not in placeholders

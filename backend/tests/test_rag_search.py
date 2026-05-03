import unittest
from unittest.mock import Mock, patch

from app.evaluators.rag_eval import run_default_rag_eval
from app.api.v1.endpoints.knowledge import ask_knowledge, search_knowledge
from app.rag.embedding_client import demo_embedding
from app.rag.reranker import filter_by_keyword_overlap, rerank_by_keyword_overlap
from app.rag.vector_store import VectorSearchResult
from app.schemas.knowledge import Citation, KnowledgeAskRequest, KnowledgeAskResponse, KnowledgeSearchRequest, KnowledgeSearchResponse
from app.schemas.knowledge import KnowledgeSearchResult
from app.tools.knowledge_tools import search_knowledge_base


class RagSearchTest(unittest.TestCase):
    """知识库检索与问答测试。"""

    def test_knowledge_search_endpoint_calls_service(self) -> None:
        response = KnowledgeSearchResponse(
            query="采购超过5万需要谁审批？",
            top_k=5,
            results=[
                KnowledgeSearchResult(
                    document_id=1,
                    document_title="采购管理制度",
                    filename="采购管理制度.md",
                    chunk_id=10,
                    chunk_index=2,
                    score=0.88,
                    chunk_text="超过 5 万元的采购需要审批。",
                )
            ],
            message="知识库检索完成。",
        )
        with patch("app.api.v1.endpoints.knowledge.search_knowledge_service", return_value=response):
            data = search_knowledge(KnowledgeSearchRequest(query="采购超过5万需要谁审批？"), db=Mock())

        self.assertEqual(data["results"][0]["filename"], "采购管理制度.md")
        self.assertIn("完成", data["message"])

    def test_knowledge_ask_endpoint_returns_citations(self) -> None:
        response = KnowledgeAskResponse(
            question="空压机 E07 报警怎么处理？",
            answer="E07 通常与压力传感器异常有关，需要检查接线和机械压力表读数。",
            citations=[
                Citation(
                    document_id=2,
                    document_title="设备维修手册_空压机",
                    filename="设备维修手册_空压机.md",
                    chunk_id=12,
                    chunk_index=7,
                    score=0.91,
                )
            ],
            message="知识库问答完成。",
        )
        with patch("app.api.v1.endpoints.knowledge.ask_knowledge_service", return_value=response):
            data = ask_knowledge(KnowledgeAskRequest(question="空压机 E07 报警怎么处理？"), db=Mock())

        self.assertTrue(data["citations"])
        self.assertIn("E07", data["answer"])

    def test_default_rag_eval_requires_database_for_real_rag(self) -> None:
        results = run_default_rag_eval()

        self.assertTrue(results)
        self.assertTrue(any(not result.passed for result in results))

    def test_demo_embedding_is_useful_for_chinese_keywords(self) -> None:
        query = demo_embedding("采购超过5万需要谁审批")
        related = demo_embedding("采购金额超过50000元时需要部门负责人、财务经理和总经理审批。")
        unrelated = demo_embedding("空压机压力传感器报警，需要检查接线和机械压力表。")

        self.assertGreater(_cosine(query, related), _cosine(query, unrelated))

    def test_reranker_keeps_related_chinese_chunk(self) -> None:
        results = [
            _chunk("空压机 E07 报警通常与压力传感器异常有关。", filename="设备维修手册_空压机.md"),
            _chunk("差旅报销需要提交交通票据和住宿发票。", filename="差旅报销制度.md"),
        ]

        ranked = rerank_by_keyword_overlap("空压机 E07 报警怎么处理？", results)
        filtered = filter_by_keyword_overlap("空压机 E07 报警怎么处理？", ranked)

        self.assertEqual(filtered[0].filename, "设备维修手册_空压机.md")
        self.assertEqual(len(filtered), 1)

    def test_reranker_drops_obviously_unrelated_query(self) -> None:
        results = [
            _chunk("采购金额超过 50000 元时需要部门负责人和财务经理审批。", filename="采购管理制度.md"),
            _chunk("空压机 E07 报警需要检查压力传感器接线。", filename="设备维修手册_空压机.md"),
        ]

        filtered = filter_by_keyword_overlap("今天外面天气怎么样？", results)

        self.assertEqual(filtered, [])

    def test_reranker_filters_cross_policy_citations_for_purchase_query(self) -> None:
        """采购制度问题不应因为“金额/审批”命中而引用差旅报销制度。"""
        results = [
            _chunk("单笔采购金额超过 50000 元应进入专项审批。", filename="采购管理制度.md"),
            _chunk("差旅报销金额超过 10000 元需要总经理审批。", filename="差旅报销制度.md"),
        ]

        filtered = filter_by_keyword_overlap("采购金额超过5万元需要怎么审批？", results)

        self.assertEqual([result.filename for result in filtered], ["采购管理制度.md"])

    def test_knowledge_tool_passes_database_session_to_service(self) -> None:
        """工具层搜索知识库时必须传入数据库会话。"""
        db = Mock()
        response = KnowledgeSearchResponse(
            query="采购超过5万怎么审批？",
            top_k=5,
            results=[],
            message="未检索到相关文档片段，请先导入知识库文档。",
        )

        with patch("app.tools.knowledge_tools.search_knowledge", return_value=response) as service_mock:
            result = search_knowledge_base(db, "采购超过5万怎么审批？")

        service_mock.assert_called_once()
        self.assertIs(service_mock.call_args.args[0], db)
        self.assertTrue(result.success)


def _cosine(left: list[float], right: list[float]) -> float:
    """计算测试用余弦相似度。"""
    return sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))


def _chunk(text: str, *, filename: str) -> VectorSearchResult:
    """构造测试用检索片段。"""
    return VectorSearchResult(
        chunk_id=1,
        document_id=1,
        chunk_text=text,
        chunk_index=1,
        score=0.8,
        filename=filename,
        document_title=filename.removesuffix(".md"),
    )


if __name__ == "__main__":
    unittest.main()

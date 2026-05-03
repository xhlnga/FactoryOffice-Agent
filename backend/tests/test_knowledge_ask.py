import unittest
from unittest.mock import Mock, patch

from app.core.exceptions import AppException
from app.rag.vector_store import VectorSearchResult
from app.schemas.knowledge import KnowledgeAskRequest
from app.services.knowledge_service import ask_knowledge


class KnowledgeAskTest(unittest.TestCase):
    """知识库问答服务测试。"""

    def test_knowledge_ask_returns_citations_from_retrieved_chunks(self) -> None:
        """有检索结果时，回答必须包含引用来源。"""
        results = [
            VectorSearchResult(
                chunk_id=10,
                document_id=1,
                chunk_text="单笔采购金额超过 50000 元时，应经过部门负责人、财务经理和总经理审批。",
                chunk_index=3,
                score=0.92,
                filename="采购管理制度.md",
                document_title="采购管理制度",
                metadata={"category": "采购流程"},
            )
        ]

        with patch("app.services.knowledge_service.retrieve_relevant_chunks", return_value=results):
            with patch("app.services.knowledge_service._has_real_llm_config", return_value=False):
                response = ask_knowledge(
                    Mock(),
                    KnowledgeAskRequest(question="采购超过 5 万需要谁审批？", top_k=3),
                )

        self.assertTrue(response.citations)
        self.assertEqual(response.citations[0].filename, "采购管理制度.md")
        self.assertIn("引用来源", response.answer)
        self.assertIn("采购管理制度", response.answer)

    def test_knowledge_ask_uses_clear_insufficient_data_message(self) -> None:
        """没有检索结果时，系统应明确说资料不足，而不是编造制度结论。"""
        with patch("app.services.knowledge_service.retrieve_relevant_chunks", return_value=[]):
            response = ask_knowledge(
                Mock(),
                KnowledgeAskRequest(question="某个不存在的设备报警代码怎么处理？", top_k=3),
            )

        self.assertEqual(response.citations, [])
        self.assertIn("知识库资料不足", response.answer)

    def test_knowledge_ask_falls_back_when_llm_fails(self) -> None:
        """LLM 调用失败时，应返回基于检索片段的兜底回答和引用，而不是整个请求失败。"""
        results = [
            VectorSearchResult(
                chunk_id=12,
                document_id=2,
                chunk_text="E07 报警通常与压力传感器、气路压力波动或过滤器压差异常有关。",
                chunk_index=5,
                score=0.88,
                filename="设备维修手册_空压机.md",
                document_title="设备维修手册_空压机",
                metadata={"category": "设备手册"},
            )
        ]

        with patch("app.services.knowledge_service.retrieve_relevant_chunks", return_value=results):
            with patch("app.services.knowledge_service._has_real_llm_config", return_value=True):
                with patch(
                    "app.services.knowledge_service.chat_completion",
                    side_effect=AppException("无法连接大模型服务。", status_code=502),
                ):
                    response = ask_knowledge(
                        Mock(),
                        KnowledgeAskRequest(question="空压机 E07 报警怎么处理？", top_k=3),
                    )

        self.assertTrue(response.citations)
        self.assertIn("兜底回答", response.answer)
        self.assertIn("设备维修手册_空压机", response.answer)


if __name__ == "__main__":
    unittest.main()

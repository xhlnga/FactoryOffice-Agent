from unittest.mock import patch

import pytest

from app.rag.query_rewriter import apply_rules, reload_mapping


class TestRuleRewriter:
    def test_longest_match_first(self):
        # "买大东西" is longer than "买大件", so it should match first
        with patch("app.rag.query_rewriter._load_mapping") as mock_load:
            mock_load.return_value = [
                {"colloquial": "买大东西", "term": "大额采购"},
                {"colloquial": "买大件", "term": "大件采购"},
            ]
            result = apply_rules("买大东西")
            assert result == "大额采购"

    def test_multiple_replacements(self):
        with patch("app.rag.query_rewriter._load_mapping") as mock_load:
            mock_load.return_value = [
                {"colloquial": "闪红灯", "term": "故障报警"},
                {"colloquial": "咋办", "term": "怎么处理"},
            ]
            result = apply_rules("机器闪红灯咋办")
            assert result == "机器故障报警怎么处理"

    def test_no_match_returns_original(self):
        with patch("app.rag.query_rewriter._load_mapping") as mock_load:
            mock_load.return_value = []
            result = apply_rules("采购制度有哪些")
            assert result == "采购制度有哪些"

    def test_reload_clears_cache(self):
        with patch("app.rag.query_rewriter._load_mapping") as mock_load:
            mock_load.return_value = [{"colloquial": "x", "term": "y"}]
            assert apply_rules("x") == "y"
            reload_mapping()
            mock_load.return_value = []
            assert apply_rules("x") == "x"

    def test_load_mapping_sorts_by_length_descending(self):
        """Verify _load_mapping actually sorts entries longest-first."""
        import json
        import tempfile
        from pathlib import Path
        from app.rag import query_rewriter

        data = {
            "replacements": [
                {"colloquial": "x", "term": "short"},
                {"colloquial": "xxx", "term": "long"},
                {"colloquial": "xx", "term": "mid"},
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f)
            tmp_path = f.name

        try:
            with patch.object(query_rewriter, "_MAPPING_PATH", Path(tmp_path)):
                query_rewriter.reload_mapping()
                result = query_rewriter._load_mapping()
                lengths = [len(r["colloquial"]) for r in result]
                assert lengths == [3, 2, 1], f"Expected [3, 2, 1], got {lengths}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_load_mapping_returns_empty_for_missing_file(self):
        from app.rag import query_rewriter
        from pathlib import Path

        with patch.object(query_rewriter, "_MAPPING_PATH", Path("/nonexistent/path/mapping.json")):
            query_rewriter.reload_mapping()
            result = query_rewriter._load_mapping()
            assert result == []

    def test_apply_rules_with_empty_string(self):
        with patch("app.rag.query_rewriter._load_mapping") as mock_load:
            mock_load.return_value = [{"colloquial": "x", "term": "y"}]
            result = apply_rules("")
            assert result == ""

    def test_rewrite_query_calls_llm_when_available(self):
        from app.rag.query_rewriter import rewrite_query

        with patch("app.rag.query_rewriter.apply_rules") as mock_rules, \
             patch("app.rag.query_rewriter._call_llm_rewrite") as mock_llm:
            mock_rules.return_value = "大额采购 审批"
            mock_llm.return_value = "采购金额较大时需要哪个层级审批"

            result = rewrite_query("那个买大东西的要找哪个领导签")

            mock_rules.assert_called_once_with("那个买大东西的要找哪个领导签")
            mock_llm.assert_called_once_with("大额采购 审批")
            assert result == "采购金额较大时需要哪个层级审批"

    def test_rewrite_query_falls_back_to_rules_when_llm_fails(self):
        from app.rag.query_rewriter import rewrite_query

        with patch("app.rag.query_rewriter.apply_rules") as mock_rules, \
             patch("app.rag.query_rewriter._call_llm_rewrite") as mock_llm:
            mock_rules.return_value = "空压机故障报警怎么处理"
            mock_llm.side_effect = RuntimeError("LLM timeout")

            result = rewrite_query("那个转的机器坏了屏幕闪红灯咋办")

            assert result == "空压机故障报警怎么处理"

    def test_rewrite_query_rules_return_original_then_llm_fails(self):
        from app.rag.query_rewriter import rewrite_query

        with patch("app.rag.query_rewriter.apply_rules") as mock_rules, \
             patch("app.rag.query_rewriter._call_llm_rewrite") as mock_llm:
            mock_rules.return_value = "干啥"
            mock_llm.side_effect = RuntimeError("LLM timeout")

            result = rewrite_query("干啥")
            assert result == "干啥"

    def test_llm_rewrite_prompt_contains_industry_context(self):
        from app.rag.query_rewriter import REWRITE_SYSTEM_PROMPT

        assert "制造业" in REWRITE_SYSTEM_PROMPT
        assert "工厂" in REWRITE_SYSTEM_PROMPT
        assert "口语" in REWRITE_SYSTEM_PROMPT

    def test_call_llm_rewrite_raises_on_empty_response(self):
        from app.rag.query_rewriter import _call_llm_rewrite

        with patch("app.services.llm_service.chat_completion") as mock_chat:
            mock_chat.return_value = "   "
            with pytest.raises(RuntimeError, match="empty response"):
                _call_llm_rewrite("test query")

    def test_query_rewrite_node_sets_effective_message(self):
        from app.agents.graph_nodes import query_rewrite_node
        from unittest.mock import patch

        state = {"message": "机器闪红灯咋办", "effective_message": "机器闪红灯咋办"}

        with patch("app.rag.query_rewriter.rewrite_query") as mock_rewrite:
            mock_rewrite.return_value = "空压机故障报警怎么处理"
            result = query_rewrite_node(state)
            assert result["effective_message"] == "空压机故障报警怎么处理"

    def test_query_rewrite_node_falls_back_to_original(self):
        from app.agents.graph_nodes import query_rewrite_node
        from unittest.mock import patch

        state = {"message": "hello", "effective_message": "hello"}

        with patch("app.rag.query_rewriter.rewrite_query") as mock_rewrite:
            mock_rewrite.side_effect = Exception("rewrite failed")
            result = query_rewrite_node(state)
            assert result["effective_message"] == "hello"

    def test_route_after_classify_needs_rewrite_low_confidence(self):
        from app.agents.graph_edges import route_after_classify

        state = {"intent": "knowledge_qa", "intent_confidence": 0.5}
        assert route_after_classify(state) == "query_rewrite"

    def test_route_after_classify_needs_rewrite_unknown(self):
        from app.agents.graph_edges import route_after_classify

        state = {"intent": "unknown"}
        assert route_after_classify(state) == "query_rewrite"

    def test_route_after_classify_skip_rewrite_high_confidence(self):
        from app.agents.graph_edges import route_after_classify

        state = {"intent": "knowledge_qa", "intent_confidence": 0.9}
        assert route_after_classify(state) == "retrieve_knowledge"

    def test_route_after_classify_rewrite_low_confidence_purchase_intent(self):
        from app.agents.graph_edges import route_after_classify

        state = {"intent": "purchase_request", "intent_confidence": 0.5}
        assert route_after_classify(state) == "query_rewrite"

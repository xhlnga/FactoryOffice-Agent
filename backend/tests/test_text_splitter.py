import re
import pytest
from app.rag.text_splitter import SplitterConfig, get_config, TextChunk, split_text


class TestStructuredSplit:
    def test_empty_text_returns_empty(self):
        result = split_text("", doc_type="general")
        assert result == []

    def test_policy_keeps_sections_together(self):
        text = "## 3. 基本原则\n\n### 3.1 业务必要性原则\n\n采购申请必须基于真实业务需求。申请部门应说明采购用途。"
        chunks = split_text(text, doc_type="policy")
        assert len(chunks) >= 1
        joined = " ".join(c.text for c in chunks)
        assert "基本原则" in joined
        assert "业务必要性原则" in joined
        assert "采购申请必须基于真实业务需求" in joined

    def test_manual_keeps_table_rows_together(self):
        text = """## 2. 适用范围

| 设备类别 | 设备示例 | 责任部门 |
|---|---|---|
| 螺杆式空压机 | AC-A01 | 设备部 |
| 储气罐 | TK-A01 | 设备部 |
| 冷冻式干燥机 | DR-A01 | 设备部 |
| 管路过滤器 | FL-A01 | 设备部 |"""
        chunks = split_text(text, doc_type="manual")
        table_chunks = [c for c in chunks if "|" in c.text]
        assert len(table_chunks) >= 1
        for tc in table_chunks:
            assert "设备类别" in tc.text

    def test_long_paragraph_breaks_at_period(self):
        text = "采购申请必须基于真实业务需求。" * 200
        chunks = split_text(text, doc_type="policy")
        assert len(chunks) > 1
        for chunk in chunks[:-1]:
            assert chunk.text.endswith("。") or chunk.text.endswith("；")

    def test_heading_at_doc_end_not_lost(self):
        text = "正文内容\n\n## 附录"
        chunks = split_text(text, doc_type="general")
        assert any("附录" in c.text for c in chunks)

    def test_chunk_metadata_contains_doc_type(self):
        text = "这是一段测试文本。"
        chunks = split_text(text, doc_type="policy")
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.metadata.get("doc_type") == "policy"


class TestSplitterConfig:
    def test_get_config_returns_policy_config(self):
        config = get_config("policy")
        assert config.chunk_size == 900
        assert config.overlap == 100

    def test_get_config_returns_manual_config(self):
        config = get_config("manual")
        assert config.chunk_size == 500
        assert config.overlap == 60

    def test_get_config_returns_general_config(self):
        config = get_config("general")
        assert config.chunk_size == 800
        assert config.overlap == 120

    def test_invalid_doc_type_uses_general(self):
        config = get_config("invalid_xyz")
        assert config.chunk_size == 800
        assert config.overlap == 120

    def test_config_heading_pattern_matches_chinese(self):
        config = get_config("policy")
        assert config.heading_pattern.search("## 3. 基本原则")
        assert config.heading_pattern.search("# 采购管理制度")
        assert not config.heading_pattern.search("普通文本行")

    def test_config_table_pattern_matches_markdown_table(self):
        config = get_config("manual")
        assert config.table_pattern.search("| 设备类别 | 设备示例 |")
        assert config.table_pattern.search("|---|---|")
        assert not config.table_pattern.search("普通文本")

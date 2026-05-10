import re
import pytest
from app.rag.text_splitter import SplitterConfig, get_config


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

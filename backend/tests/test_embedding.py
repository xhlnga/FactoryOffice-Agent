import pytest
from unittest.mock import patch

import app.rag.embedding_client as _embedding_mod
from app.rag.embedding_client import (
    DemoEmbeddingClient,
    embed_text,
    embed_texts,
)


class TestDemoEmbedding:
    @pytest.fixture(autouse=True)
    def _force_demo_client(self):
        """Force DemoEmbeddingClient to avoid loading the heavy BGE model."""
        with patch.object(_embedding_mod, "get_embedding_client",
                          return_value=DemoEmbeddingClient()):
            yield

    def test_single_text_returns_vector(self):
        vec = embed_text("空压机 E07 报警排查")
        assert len(vec) == 1024
        assert all(isinstance(v, float) for v in vec)

    def test_batch_returns_multiple_vectors(self):
        texts = ["采购审批流程", "质量异常处理", "设备维修工单"]
        vecs = embed_texts(texts)
        assert len(vecs) == 3
        assert all(len(v) == 1024 for v in vecs)

    def test_different_texts_produce_different_vectors(self):
        v1 = embed_text("采购审批流程")
        v2 = embed_text("设备维修工单")
        assert v1 != v2

    def test_demo_client_dimension_configurable(self):
        client = DemoEmbeddingClient(dimensions=384)
        vec = client.embed("测试")
        assert len(vec) == 384


class TestLocalBGECache:
    def test_local_bge_cache_is_reused(self):
        """get_embedding_client() 在 provider=local 时应缓存实例。"""
        from app.rag.embedding_client import get_embedding_client, LocalBGEClient
        from app.rag.embedding_client import _embedding_client as _global
        import app.rag.embedding_client as mod

        saved = mod._embedding_client
        mod._embedding_client = None
        try:
            # Mock LocalBGEClient to avoid downloading the model
            from unittest.mock import patch
            with patch.object(mod, 'LocalBGEClient') as mock_client:
                mock_client.return_value = object()
                client1 = mod.get_embedding_client()
                client2 = mod.get_embedding_client()
                assert client1 is client2
        finally:
            mod._embedding_client = saved

import pytest
from app.retrieval.bm25_index import BM25Index, BM25Result


class TestBM25Result:
    def test_create_result(self):
        r = BM25Result(chunk_id=1, score=2.5)
        assert r.chunk_id == 1
        assert r.score == 2.5


class TestBM25Index:
    @pytest.fixture
    def sample_chunks(self):
        class FakeChunk:
            def __init__(self, id, text):
                self.id = id
                self.chunk_text = text
        return [
            FakeChunk(1, "采购金额超过50000元需要部门负责人和财务经理审批"),
            FakeChunk(2, "空压机E07报警通常与压力传感器异常有关"),
            FakeChunk(3, "差旅报销需要提交交通票据和住宿发票"),
        ]

    def test_build_and_search(self, sample_chunks):
        index = BM25Index()
        index.build(sample_chunks)
        results = index.search("采购超过5万怎么审批", top_k=2)
        assert len(results) <= 2
        assert all(isinstance(r, BM25Result) for r in results)
        assert results[0].chunk_id == 1

    def test_search_empty_index(self):
        index = BM25Index()
        results = index.search("采购审批", top_k=5)
        assert results == []

    def test_add_and_remove(self, sample_chunks):
        index = BM25Index()
        index.build(sample_chunks[:2])

        class FakeChunk:
            pass
        c = FakeChunk()
        c.id = 3
        c.chunk_text = "差旅报销需要提交交通票据和住宿发票"
        index.add(c)

        results = index.search("差旅报销", top_k=3)
        assert any(r.chunk_id == 3 for r in results)

        index.remove(3)
        results2 = index.search("差旅报销", top_k=3)
        assert all(r.chunk_id != 3 for r in results2)

    def test_build_rebuilds(self, sample_chunks):
        index = BM25Index()
        index.build(sample_chunks[:1])
        assert len(index.search("空压机报警", top_k=3)) <= 1
        index.build(sample_chunks)
        assert any(r.chunk_id == 2 for r in index.search("空压机报警", top_k=3))

    def test_tokenize_fallback_to_chars(self):
        tokens = BM25Index._tokenize("123!")
        assert len(tokens) >= 1

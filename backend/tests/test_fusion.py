import pytest
from app.rag.vector_store import VectorSearchResult
from app.retrieval.bm25_index import BM25Result
from app.retrieval.fusion import fuse_results


def _v(chunk_id: int, score: float, filename: str = "test.md") -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=chunk_id, document_id=1,
        chunk_text=f"chunk {chunk_id}", chunk_index=chunk_id,
        score=score, filename=filename, document_title="Test",
    )


def _b(chunk_id: int, score: float) -> BM25Result:
    return BM25Result(chunk_id=chunk_id, score=score)


class TestFusion:
    def test_weighted_fusion_with_high_variance(self):
        vec = [_v(1, 0.9), _v(2, 0.7), _v(3, 0.5)]
        bm25 = [_b(2, 8.0), _b(1, 5.0), _b(3, 2.0)]
        result = fuse_results(vec, bm25, alpha=0.5)
        assert len(result) >= 1
        assert result[0].chunk_id == 1

    def test_rrf_when_scores_flat(self):
        vec = [_v(1, 0.35), _v(2, 0.34), _v(3, 0.33)]
        bm25 = [_b(3, 7.0), _b(2, 5.0), _b(1, 3.0)]
        result = fuse_results(vec, bm25, alpha=0.5)
        assert len(result) >= 1

    def test_chunk_in_one_path_still_ranked(self):
        vec = [_v(1, 0.9), _v(2, 0.8)]
        bm25 = [_b(3, 5.0)]
        result = fuse_results(vec, bm25, alpha=0.5)
        ids = {r.chunk_id for r in result}
        assert 1 in ids and 3 in ids

    def test_empty_inputs(self):
        assert fuse_results([], [], alpha=0.5) == []

    def test_alpha_0_full_bm25(self):
        vec = [_v(1, 0.9), _v(2, 0.7)]
        bm25 = [_b(2, 9.0), _b(1, 3.0)]
        result = fuse_results(vec, bm25, alpha=0.0)
        assert result[0].chunk_id == 2

    def test_alpha_1_full_vector(self):
        vec = [_v(1, 0.9), _v(2, 0.7)]
        bm25 = [_b(2, 9.0), _b(1, 3.0)]
        result = fuse_results(vec, bm25, alpha=1.0)
        assert result[0].chunk_id == 1

    def test_fuse_results_passes_query_to_domain_detection(self):
        from app.retrieval.fusion import fuse_results
        from app.rag.vector_store import VectorSearchResult

        vec = [
            VectorSearchResult(chunk_id=1, chunk_text="大额采购需部门经理审批", score=0.85,
                               document_id=1, document_title="采购制度", filename="p.md",
                               chunk_index=0)
        ]
        fused = fuse_results(vec, [], alpha=0.5, query="采购超过5万需要谁审批")
        assert len(fused) == 1

    def test_fuse_results_with_empty_query(self):
        from app.retrieval.fusion import fuse_results
        from app.rag.vector_store import VectorSearchResult

        vec = [
            VectorSearchResult(chunk_id=1, chunk_text="text", score=0.5,
                               document_id=1, document_title="", filename="f",
                               chunk_index=0)
        ]
        fused = fuse_results(vec, [], alpha=0.5, query="")
        assert len(fused) == 1

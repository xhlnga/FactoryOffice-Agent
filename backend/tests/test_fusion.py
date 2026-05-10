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

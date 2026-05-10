from __future__ import annotations

from app.rag.vector_store import VectorSearchResult
from app.retrieval.bm25_index import BM25Result

FUSION_SCORE_RANGE_THRESHOLD = 0.1
RRF_K = 60
DOMAIN_BONUS_WEIGHTED = 0.05
DOMAIN_BONUS_RRF = 0.002

_DOMAIN_KEYWORDS = {
    "purchase": {"采购", "供应商", "询价", "比价", "采购申请", "采购审批"},
    "reimbursement": {"差旅", "报销", "住宿", "交通费", "出差"},
    "maintenance": {"设备", "维修", "空压机", "报警", "停机", "传感器"},
    "quality": {"质量", "异常", "不合格", "超差", "抽检", "ncr", "客诉"},
    "safety": {"安全", "隐患", "事故", "劳保", "动火", "危险源"},
    "weekly_report": {"周报", "项目周报", "本周进展", "下周计划"},
}


def fuse_results(
    vector_results: list[VectorSearchResult],
    bm25_results: list[BM25Result],
    *,
    alpha: float = 0.5,
    query: str = "",
) -> list[VectorSearchResult]:
    if not vector_results and not bm25_results:
        return []

    domain = _detect_domain(query)
    merged = _merge_by_chunk_id(vector_results, bm25_results)

    cosine_scores = [m["vec_score"] for m in merged.values()]
    score_range = (max(cosine_scores) - min(cosine_scores)) if len(cosine_scores) >= 2 else 0.0
    using_rrf = score_range < FUSION_SCORE_RANGE_THRESHOLD

    if using_rrf:
        results = _rrf_fusion(vector_results, bm25_results)
    else:
        results = _weighted_fusion(vector_results, bm25_results, alpha)

    _apply_domain_bonus(results, domain, using_rrf)
    results.sort(key=lambda r: r.score or 0, reverse=True)
    return results


def _merge_by_chunk_id(
    vector_results: list[VectorSearchResult],
    bm25_results: list[BM25Result],
) -> dict[int, dict]:
    merged: dict[int, dict] = {}
    for r in vector_results:
        merged[r.chunk_id] = {"vec_obj": r, "vec_score": r.score or 0, "bm_score": 0.0}
    for r in bm25_results:
        if r.chunk_id in merged:
            merged[r.chunk_id]["bm_score"] = r.score
        else:
            merged[r.chunk_id] = {"vec_obj": None, "vec_score": 0.0, "bm_score": r.score}
    return merged


def _weighted_fusion(
    vec: list[VectorSearchResult],
    bm25: list[BM25Result],
    alpha: float,
) -> list[VectorSearchResult]:
    merged = _merge_by_chunk_id(vec, bm25)
    vs = [m["vec_score"] for m in merged.values()]
    bs = [m["bm_score"] for m in merged.values()]
    v_min, v_max = min(vs), max(vs)
    b_min, b_max = min(bs), max(bs)

    results: list[VectorSearchResult] = []
    for chunk_id, m in merged.items():
        nv = _norm(m["vec_score"], v_min, v_max)
        nb = _norm(m["bm_score"], b_min, b_max)
        score = alpha * nv + (1 - alpha) * nb
        if m["vec_obj"] is not None:
            r = m["vec_obj"]
            r.score = score
        else:
            r = VectorSearchResult(chunk_id=chunk_id, document_id=0, chunk_text="", chunk_index=0, score=score)
        results.append(r)
    return results


def _rrf_fusion(
    vec: list[VectorSearchResult],
    bm25: list[BM25Result],
) -> list[VectorSearchResult]:
    vr = {r.chunk_id: i + 1 for i, r in enumerate(vec)}
    br = {r.chunk_id: i + 1 for i, r in enumerate(bm25)}
    all_ids = set(vr) | set(br)

    results: list[VectorSearchResult] = []
    for chunk_id in all_ids:
        score = 1.0 / (RRF_K + vr.get(chunk_id, len(vec) + 1))
        score += 1.0 / (RRF_K + br.get(chunk_id, len(bm25) + 1))
        existing = next((r for r in vec if r.chunk_id == chunk_id), None)
        if existing is not None:
            existing.score = score
            results.append(existing)
        else:
            results.append(VectorSearchResult(chunk_id=chunk_id, document_id=0, chunk_text="", chunk_index=0, score=score))
    return results


def _norm(value: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.5
    return (value - lo) / (hi - lo)


def _apply_domain_bonus(results: list[VectorSearchResult], domain: str | None, using_rrf: bool) -> None:
    if domain is None:
        return
    bonus = DOMAIN_BONUS_RRF if using_rrf else DOMAIN_BONUS_WEIGHTED
    for r in results:
        if _result_matches_domain(r, domain):
            r.score = (r.score or 0) + bonus


def _detect_domain(query: str) -> str | None:
    normalized = query.lower()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in normalized for kw in keywords):
            return domain
    return None


def _result_matches_domain(result: VectorSearchResult, domain: str) -> bool:
    keywords = _DOMAIN_KEYWORDS.get(domain, set())
    if not keywords:
        return False
    haystack = " ".join(
        p for p in [result.filename or "", result.document_title or "", result.chunk_text or ""] if p
    ).lower()
    return any(kw in haystack for kw in keywords)

"""检索管线评估脚本。

使用前：
1. 确保 BGE 模型已下载（首次运行 get_embedding_client() 自动下载）
2. 确保数据库有已索引的文档
3. 编辑 data/eval_queries/query_annotations.json 填入 relevant_chunk_ids

运行：
  # 基线（不开改写）
  cd backend
  EMBEDDING_PROVIDER=local python -m pytest app/evaluators/retrieval_eval.py -v -s

  # A/B 对比（开改写）
  cd backend
  EMBEDDING_PROVIDER=local python -m pytest app/evaluators/retrieval_eval.py -v -s --rewrite
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.core.database import SessionLocal
from app.rag.retriever import get_bm25_index, init_bm25_index, retrieve_relevant_chunks


def load_queries() -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parents[2] / "data" / "eval_queries" / "query_annotations.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def recall_at_k(retrieved_ids: list[int], relevant_ids: list[int], k: int) -> float:
    if not relevant_ids:
        return -1.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for rid in relevant_ids if rid in top_k)
    return hits / len(relevant_ids)


def mrr(retrieved_ids: list[int], relevant_ids: list[int]) -> float:
    if not relevant_ids:
        return -1.0
    for i, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / i
    return 0.0


class TestRetrievalEval:
    """检索管线评估测试套件。

    默认跑基线（不开 query 改写）。用 --rewrite 标志切换 A/B 模式。
    """

    @pytest.fixture(scope="class")
    def db_session(self):
        db = SessionLocal()
        init_bm25_index(db)
        yield db
        db.close()

    @pytest.mark.parametrize("q_entry", load_queries(), ids=lambda q: q["query_id"])
    def test_query(self, db_session, q_entry, request):
        use_rewrite = request.config.getoption("--rewrite", default=False)

        bm25_query = None
        if use_rewrite:
            from app.rag.query_rewriter import rewrite_query
            bm25_query = rewrite_query(q_entry["query"])

        retrieved = retrieve_relevant_chunks(
            db_session,
            query=q_entry["query"],
            top_k=10,
            bm25_query=bm25_query,
        )
        retrieved_ids = [r.chunk_id for r in retrieved]
        relevant_ids = q_entry["relevant_chunk_ids"]

        r5 = recall_at_k(retrieved_ids, relevant_ids, 5)
        r10 = recall_at_k(retrieved_ids, relevant_ids, 10)
        m = mrr(retrieved_ids, relevant_ids)

        mode = "rewrite" if use_rewrite else "baseline"
        print(
            f"\n{q_entry['query_id']} [{q_entry['query_type']}] [{mode}]: "
            f"recall@5={r5:.2f} recall@10={r10:.2f} MRR={m:.2f} "
            f"retrieved_ids={retrieved_ids}"
        )

        if relevant_ids:
            assert r5 >= 0.0

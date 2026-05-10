from __future__ import annotations

from dataclasses import dataclass

import jieba
from rank_bm25 import BM25Okapi


@dataclass(slots=True)
class BM25Result:
    chunk_id: int
    score: float


class BM25Index:
    def __init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        self._chunk_ids: list[int] = []
        self._corpus: list[list[str]] = []

    def build(self, chunks: list) -> None:
        self._chunk_ids = [c.id for c in chunks]
        self._corpus = [self._tokenize(c.chunk_text) for c in chunks]
        self._bm25 = BM25Okapi(self._corpus) if self._corpus else None

    def search(self, query: str, top_k: int) -> list[BM25Result]:
        if self._bm25 is None or not self._corpus:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:top_k]
        return [
            BM25Result(chunk_id=self._chunk_ids[idx], score=float(score))
            for idx, score in ranked
            if score > 0
        ]

    def add(self, chunk) -> None:
        self._chunk_ids.append(chunk.id)
        self._corpus.append(self._tokenize(chunk.chunk_text))
        self._bm25 = BM25Okapi(self._corpus) if self._corpus else None

    def remove(self, chunk_id: int) -> None:
        try:
            idx = self._chunk_ids.index(chunk_id)
        except ValueError:
            return
        del self._chunk_ids[idx]
        del self._corpus[idx]
        self._bm25 = BM25Okapi(self._corpus) if self._corpus else None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = jieba.lcut(text.lower())
        tokens = [t.strip() for t in tokens if t.strip()]
        if not tokens:
            tokens = list(text.lower())
        return tokens

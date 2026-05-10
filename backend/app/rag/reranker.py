import re

from app.rag.vector_store import VectorSearchResult


def rerank_by_keyword_overlap(
    query: str,
    results: list[VectorSearchResult],
) -> list[VectorSearchResult]:
    """基于关键词重合的轻量重排。

    这是可解释的兜底方案，后续可替换为专用 reranker 模型。
    """
    query_terms = _tokenize(query)
    if not query_terms:
        return results

    return sorted(
        results,
        key=lambda result: (
            _domain_score(query, result),
            _overlap_score(query_terms, result.chunk_text),
            result.score or 0,
        ),
        reverse=True,
    )


def filter_by_keyword_overlap(
    query: str,
    results: list[VectorSearchResult],
) -> list[VectorSearchResult]:
    """过滤明显无关的检索结果。

    向量检索会天然返回 top_k，但企业知识库不能为了返回而返回。
    当问题和片段没有任何可解释关键词交集时，宁可提示资料不足，也不要引用无关制度。
    """
    query_terms = _tokenize(query)
    if not query_terms:
        return results

    filtered = [
        result
        for result in results
        if _overlap_score(query_terms, result.chunk_text) > 0
    ]
    domain = _detect_domain(query)
    if domain is None:
        return filtered

    domain_results = [result for result in filtered if _result_matches_domain(result, domain)]
    return domain_results or filtered


def _tokenize(text: str) -> set[str]:
    """使用 jieba 分词，兼容中文和英文数字。"""
    try:
        import jieba
    except ImportError:
        return _tokenize_ngram_fallback(text)

    normalized = text.lower()
    ascii_terms = set(re.findall(r"[a-z0-9][a-z0-9_-]{1,}", normalized))
    chinese_terms = set(jieba.cut(text, cut_all=False))
    return {
        term.strip()
        for term in ascii_terms | chinese_terms
        if term.strip() and term.strip() not in _STOP_TERMS
    }


def _tokenize_ngram_fallback(text: str) -> set[str]:
    """n-gram 降级方案，当 jieba 不可用时使用。"""
    normalized = text.lower()
    ascii_terms = set(re.findall(r"[a-z0-9][a-z0-9_-]{1,}", normalized))
    chinese_chars = re.findall(r"[一-鿿]", text)
    chinese_terms: set[str] = set()
    for size in (2, 3, 4):
        if len(chinese_chars) < size:
            continue
        chinese_terms.update(
            "".join(chinese_chars[index:index + size])
            for index in range(len(chinese_chars) - size + 1)
        )
    return {
        term
        for term in ascii_terms | chinese_terms
        if term not in _STOP_TERMS
    }


def _overlap_score(query_terms: set[str], text: str) -> int:
    """计算查询关键词在文本中的命中数量。"""
    text_terms = _tokenize(text)
    return len(query_terms & text_terms)


def _domain_score(query: str, result: VectorSearchResult) -> int:
    """按业务域给检索结果加权，避免跨制度误排在前面。"""
    domain = _detect_domain(query)
    if domain is None:
        return 0
    return 1 if _result_matches_domain(result, domain) else 0


def _detect_domain(query: str) -> str | None:
    """识别问题所属业务域，只处理边界较清楚的制造业办公场景。"""
    normalized = query.lower()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return domain
    return None


def _result_matches_domain(result: VectorSearchResult, domain: str) -> bool:
    """判断检索结果是否属于指定业务域。"""
    keywords = _DOMAIN_KEYWORDS[domain]
    metadata_text = " ".join(str(value) for value in result.metadata.values())
    primary_haystack = " ".join(
        part
        for part in [
            result.filename or "",
            result.document_title or "",
            metadata_text,
        ]
        if part
    ).lower()
    if primary_haystack:
        return any(keyword in primary_haystack for keyword in keywords)

    return any(keyword in result.chunk_text.lower() for keyword in keywords)


_STOP_TERMS = {
    "今天", "明天", "后天",
    "怎么", "如何", "是否", "什么", "多少",
    "需要", "可以", "应该", "必须",
    "一下", "这个", "那个",
    "相关", "当前", "本周", "下周",
    "的", "了", "是", "在", "和", "与", "或",
}


_DOMAIN_KEYWORDS = {
    "purchase": {"采购", "供应商", "询价", "比价", "采购申请", "采购审批"},
    "reimbursement": {"差旅", "报销", "住宿", "交通费", "出差"},
    "maintenance": {"设备", "维修", "空压机", "报警", "停机", "传感器"},
    "quality": {"质量", "异常", "不合格", "超差", "抽检", "ncr", "客诉"},
    "safety": {"安全", "隐患", "事故", "劳保", "动火", "危险源"},
    "weekly_report": {"周报", "项目周报", "本周进展", "下周计划"},
}

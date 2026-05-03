from app.evaluators.test_cases import DEFAULT_RAG_EVAL_CASES, EvalFinding, EvalResult, RagEvalCase
from app.schemas.knowledge import Citation, KnowledgeAskResponse
from app.services.knowledge_service import ask_knowledge
from app.schemas.knowledge import KnowledgeAskRequest
from sqlalchemy.orm import Session


def evaluate_rag_response(case: RagEvalCase, response: KnowledgeAskResponse) -> EvalResult:
    """评测单条知识库问答结果。"""
    findings = [
        _check_answer_keywords(case, response.answer),
        _check_forbidden_phrases(case, response.answer),
        _check_citations(case, response.citations),
        _check_citation_keywords(case, response.citations),
        _check_no_placeholder_answer(response.answer),
    ]
    return _build_result(case.case_id, findings)


def run_default_rag_eval(db: Session | None = None) -> list[EvalResult]:
    """运行默认知识库问答评测。"""
    results: list[EvalResult] = []
    for case in DEFAULT_RAG_EVAL_CASES:
        if db is None:
            response = KnowledgeAskResponse(
                question=case.question,
                answer="知识库评测需要数据库会话和已导入文档，当前未执行真实 RAG 检索。",
                citations=[],
                message="未提供数据库会话。",
            )
        else:
            response = ask_knowledge(db, KnowledgeAskRequest(question=case.question))
        results.append(evaluate_rag_response(case, response))
    return results


def _check_answer_keywords(case: RagEvalCase, answer: str) -> EvalFinding:
    """检查回答是否覆盖业务关键词。"""
    missing = [keyword for keyword in case.expected_keywords if keyword not in answer]
    return EvalFinding(
        passed=not missing,
        check_name="answer_keywords",
        message="回答覆盖了预期业务关键词。" if not missing else "回答缺少预期业务关键词。",
        details={"missing_keywords": missing},
    )


def _check_forbidden_phrases(case: RagEvalCase, answer: str) -> EvalFinding:
    """检查回答是否出现不符合企业场景的话术。"""
    matched = [phrase for phrase in case.forbidden_phrases if phrase in answer]
    return EvalFinding(
        passed=not matched,
        check_name="forbidden_phrases",
        message="回答未出现禁用话术。" if not matched else "回答出现了不合适的话术。",
        details={"matched_phrases": matched},
    )


def _check_citations(case: RagEvalCase, citations: list[Citation]) -> EvalFinding:
    """企业知识库回答必须尽量带引用来源。"""
    passed = bool(citations) if case.require_citations else True
    return EvalFinding(
        passed=passed,
        check_name="citations_required",
        message="回答包含引用来源。" if passed else "回答缺少引用来源，企业知识库场景不可靠。",
        details={"citation_count": len(citations)},
    )


def _check_citation_keywords(case: RagEvalCase, citations: list[Citation]) -> EvalFinding:
    """检查引用来源是否像来自正确文档。"""
    if not case.expected_citation_keywords:
        return EvalFinding(True, "citation_keywords", "该用例不要求引用关键词。")

    citation_text = " ".join(
        filter(
            None,
            [
                citation.document_title
                for citation in citations
            ]
            + [citation.filename for citation in citations],
        )
    )
    missing = [keyword for keyword in case.expected_citation_keywords if keyword not in citation_text]
    return EvalFinding(
        passed=not missing,
        check_name="citation_keywords",
        message="引用来源匹配预期业务文档。" if not missing else "引用来源未匹配预期业务文档。",
        details={"missing_citation_keywords": missing},
    )


def _check_no_placeholder_answer(answer: str) -> EvalFinding:
    """避免把待接入提示当成真实知识库回答。"""
    placeholder_keywords = ["待接入", "后续将接入", "placeholder"]
    matched = [keyword for keyword in placeholder_keywords if keyword in answer]
    return EvalFinding(
        passed=not matched,
        check_name="no_placeholder_answer",
        message="回答不是占位内容。" if not matched else "回答仍是占位内容。",
        details={"matched_keywords": matched},
    )


def _build_result(case_id: str, findings: list[EvalFinding]) -> EvalResult:
    """根据检查项生成总分。"""
    passed_count = sum(1 for finding in findings if finding.passed)
    score = passed_count / len(findings) if findings else 0
    return EvalResult(
        case_id=case_id,
        passed=all(finding.passed for finding in findings),
        score=round(score, 4),
        findings=findings,
    )

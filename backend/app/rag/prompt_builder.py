from app.rag.vector_store import VectorSearchResult


SYSTEM_PROMPT = """你是制造业企业知识库助手。
回答必须基于提供的资料片段。
如果资料不足，请明确说明“当前知识库资料不足以确认”。
涉及制度、审批、维修、安全、质量流程时，必须谨慎，不要编造条款。
涉及安全、质量、客户交付、预算或正式业务动作时，要提醒用户按企业流程人工确认。
"""


def build_context(results: list[VectorSearchResult]) -> str:
    """把检索结果整理为提示词上下文。"""
    blocks: list[str] = []
    for index, result in enumerate(results, start=1):
        source = result.document_title or result.filename or f"document:{result.document_id}"
        blocks.append(
            "\n".join(
                [
                    f"[资料 {index}]",
                    f"来源：{source}",
                    f"切块：{result.chunk_index}",
                    f"内容：{result.chunk_text}",
                ]
            )
        )
    return "\n\n".join(blocks)


def build_citation_label(result: VectorSearchResult) -> str:
    """生成引用来源展示文本。"""
    source = result.document_title or result.filename or f"document:{result.document_id}"
    return f"{source}，chunk {result.chunk_index}"


def build_rag_messages(
    *,
    question: str,
    results: list[VectorSearchResult],
) -> list[dict[str, str]]:
    """构造 OpenAI-compatible chat messages。"""
    context = build_context(results)
    user_prompt = f"""请根据下面的企业知识库资料回答问题。

问题：
{question}

资料：
{context or "当前没有检索到相关资料。"}

回答要求：
1. 先给出直接回答。
2. 如果资料不足，请明确说明。
3. 涉及高风险事项时，提醒人工确认和责任部门。
4. 最后列出引用来源，格式为“文件名/文档标题 + 切块编号”。
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

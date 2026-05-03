import hashlib
import math
import re

from app.core.config import settings
from app.services.llm_service import embedding


def embed_text(text: str) -> list[float]:
    """把单段文本转换为向量。

    有可用 Embedding 配置时调用 OpenAI-compatible 接口。
    本地演示环境没有 API Key 时，使用确定性演示向量，保证 RAG 入库和检索流程能跑通。
    """
    if not has_real_embedding_config():
        return demo_embedding(text)
    return embedding(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量生成向量。

    当前逐条调用，后续可替换为批量 embedding 接口。
    """
    return [embed_text(text) for text in texts]


def has_real_embedding_config() -> bool:
    """判断是否具备真实 Embedding 配置。"""
    return _is_real_config(settings.embedding_base_url, settings.embedding_api_key)


def demo_embedding(text: str, dimensions: int = 1536) -> list[float]:
    """生成本地演示向量。

    这不是语义向量，只用于无外部 API Key 时跑通 pgvector 入库和检索流程。
    正式知识库问答应使用真实 Embedding 模型。
    """
    vector = [0.0] * dimensions
    tokens = _tokenize_for_demo_embedding(text)
    if not tokens:
        tokens = [text[:64] or "empty"]

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _tokenize_for_demo_embedding(text: str) -> list[str]:
    """为本地演示向量做中文友好的轻量切词。

    中文制度和 SOP 往往没有空格。如果只按空格切词，整段中文会变成一个 token，
    没有真实 Embedding API 时检索效果会非常差。这里用字母数字词 + 中文 2/3/4 gram
    做确定性兜底，保证“采购审批”“质量异常”“空压机报警”等中文查询能命中相关片段。
    """
    normalized = text.lower().replace("\n", " ")
    ascii_tokens = re.findall(r"[a-z0-9][a-z0-9_-]{1,}", normalized)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)

    chinese_ngrams: list[str] = []
    for size in (2, 3, 4):
        if len(chinese_chars) < size:
            continue
        chinese_ngrams.extend(
            "".join(chinese_chars[index:index + size])
            for index in range(len(chinese_chars) - size + 1)
        )

    return ascii_tokens + chinese_ngrams


def _is_real_config(base_url: str, api_key: str) -> bool:
    """过滤空配置和示例占位密钥。"""
    if not base_url or not api_key:
        return False
    placeholders = {"your_api_key_here", "your_embedding_key_here", "changeme", "placeholder"}
    return api_key.strip().lower() not in placeholders

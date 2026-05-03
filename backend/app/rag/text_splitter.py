import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TextChunk:
    """文档切块结果。"""

    text: str
    index: int
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_text(text: str) -> str:
    """规范化文本空白，避免切块时出现大量空行。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(
    text: str,
    *,
    chunk_size: int = 800,
    overlap: int = 120,
    metadata: dict[str, Any] | None = None,
) -> list[TextChunk]:
    """把长文本切成适合检索的片段。

    先按段落聚合，超长段落再按字符窗口切分。
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须大于等于 0 且小于 chunk_size")

    text = normalize_text(text)
    if not text:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in _split_paragraphs(text):
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_sliding_window(paragraph, chunk_size=chunk_size, overlap=overlap))
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    base_metadata = metadata or {}
    return [
        TextChunk(
            text=chunk,
            index=index,
            metadata={**base_metadata, "chunk_size": len(chunk)},
        )
        for index, chunk in enumerate(chunks)
    ]


def _split_paragraphs(text: str) -> list[str]:
    """按空行切段，兼容普通制度文档和会议纪要。"""
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _sliding_window(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """对超长段落使用滑动窗口切分。"""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [chunk for chunk in chunks if chunk]


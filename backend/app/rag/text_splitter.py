from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SplitterConfig:
    chunk_size: int
    overlap: int
    heading_pattern: re.Pattern = field(repr=False)
    table_pattern: re.Pattern = field(repr=False)


POLICY_CONFIG = SplitterConfig(
    chunk_size=900,
    overlap=100,
    heading_pattern=re.compile(r"^#{1,6}\s"),
    table_pattern=re.compile(r"^\|.*\|"),
)

MANUAL_CONFIG = SplitterConfig(
    chunk_size=500,
    overlap=60,
    heading_pattern=re.compile(r"^#{1,6}\s"),
    table_pattern=re.compile(r"^\|.*\|"),
)

GENERAL_CONFIG = SplitterConfig(
    chunk_size=800,
    overlap=120,
    heading_pattern=re.compile(r"^#{1,6}\s"),
    table_pattern=re.compile(r"^\|.*\|"),
)

_CONFIG_REGISTRY = {
    "policy": POLICY_CONFIG,
    "manual": MANUAL_CONFIG,
    "general": GENERAL_CONFIG,
}


def get_config(doc_type: str) -> SplitterConfig:
    return _CONFIG_REGISTRY.get(doc_type, GENERAL_CONFIG)


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
    doc_type: str = "general",
    metadata: dict[str, Any] | None = None,
) -> list[TextChunk]:
    if not text or not text.strip():
        return []

    config = get_config(doc_type)
    text = normalize_text(text)
    if not text:
        return []

    segments = _split_by_boundaries(text, config)
    base_metadata = metadata or {}
    base_metadata["doc_type"] = doc_type

    chunks: list[TextChunk] = []
    current = ""
    for segment in segments:
        if len(segment) <= config.chunk_size:
            candidate = f"{current}\n\n{segment}".strip() if current else segment
            if len(candidate) <= config.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(TextChunk(text=current, index=len(chunks), metadata=dict(base_metadata)))
                result = _maybe_table_block(segment, config)
                if isinstance(result, list):
                    for chunk_text in result:
                        chunks.append(TextChunk(text=chunk_text, index=len(chunks), metadata=dict(base_metadata)))
                    current = ""
                else:
                    current = result
        else:
            if current:
                chunks.append(TextChunk(text=current, index=len(chunks), metadata=dict(base_metadata)))
                current = ""
            sub_chunks = _split_long_segment(segment, config)
            for sub in sub_chunks:
                chunks.append(TextChunk(text=sub, index=len(chunks), metadata=dict(base_metadata)))

    if current:
        if isinstance(current, list):
            for chunk_text in current:
                chunks.append(TextChunk(text=chunk_text, index=len(chunks), metadata=dict(base_metadata)))
        else:
            chunks.append(TextChunk(text=current, index=len(chunks), metadata=dict(base_metadata)))

    return chunks


def _is_boundary_line(line: str, config: SplitterConfig) -> bool:
    return bool(config.heading_pattern.match(line) or config.table_pattern.match(line))


def _split_by_boundaries(text: str, config: SplitterConfig) -> list[str]:
    lines = text.split("\n")
    segments: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                segments.append("\n".join(current))
                current = []
            continue
        if _is_boundary_line(stripped, config):
            if current and not _is_boundary_line(current[0].strip(), config):
                segments.append("\n".join(current))
                current = []
            current.append(line)
        else:
            current.append(line)

    if current:
        segments.append("\n".join(current))

    return segments


def _maybe_table_block(segment: str, config: SplitterConfig) -> "str | list[str]":
    lines = segment.split("\n")
    is_table = all(
        config.table_pattern.match(line.strip())
        for line in lines
        if line.strip()
    )
    if not is_table or len(segment) <= config.chunk_size:
        return segment

    header = lines[0]
    header_len = len(header)
    data_lines = lines[1:]
    if not data_lines:
        return segment

    chunks: list[str] = []
    current_chunk_lines = [header]
    current_len = header_len

    for row in data_lines:
        row_len = len(row) + 1
        if current_len + row_len > config.chunk_size and len(current_chunk_lines) > 1:
            chunks.append("\n".join(current_chunk_lines))
            current_chunk_lines = [header]
            current_len = header_len
        current_chunk_lines.append(row)
        current_len += row_len

    if len(current_chunk_lines) > 1:
        chunks.append("\n".join(current_chunk_lines))

    return chunks if chunks else segment


def _split_long_segment(segment: str, config: SplitterConfig) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(segment):
        end = min(start + config.chunk_size, len(segment))
        if end < len(segment):
            lookback = max(1, int(config.chunk_size * 0.15))
            search_start = max(start, end - lookback)
            sub = segment[search_start:end]
            best = -1
            for char in ("。", "；", "\n"):
                pos = sub.rfind(char)
                if pos > best:
                    best = pos
            if best >= 0:
                end = search_start + best + 1
        chunks.append(segment[start:end].strip())
        if end >= len(segment):
            break
        start = end - config.overlap
        if start <= 0:
            start = min(config.overlap, len(segment) - 1)
    return [c for c in chunks if c]


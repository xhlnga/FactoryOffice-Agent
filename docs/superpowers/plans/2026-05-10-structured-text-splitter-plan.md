# 结构化文本切分器 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重写 `text_splitter.py`，用结构边界感知（标题 + 表格 + 空行）+ 文档类型感知（policy/manual/general）的二次切分替换现有纯段落聚合切分。

**Architecture:** 新建 `SplitterConfig` dataclass 承载三种文档类型的切分配置，重写 `split_text()` 函数（保留原函数签名兼容），内部先按结构边界切段再按文档类型定长二次切分。`TextChunk` 接口不变。

**Tech Stack:** Python stdlib `re`、`dataclasses`；Alembic migration；pytest

---

## File Structure

```
backend/
├── alembic/versions/
│   └── 20260510_0008_add_doc_type.py         # CREATE: migration
├── app/
│   ├── models/
│   │   └── document.py                        # MODIFY: +doc_type column
│   ├── schemas/
│   │   └── document.py                        # MODIFY: +doc_type in DocumentCreate
│   ├── rag/
│   │   └── text_splitter.py                   # REWRITE: StructuredTextSplitter
│   └── services/
│       └── document_service.py                # MODIFY: pass doc_type to split_text
├── tests/
│   └── test_text_splitter.py                  # CREATE: 9 tests
scripts/
└── ingest_demo_docs.py                        # MODIFY: pass doc_type to split_text
```

---

### Task 1: Add doc_type column to Document model + migration

**Files:**
- Modify: `app/models/document.py`
- Create: `alembic/versions/20260510_0008_add_doc_type.py`

- [ ] **Step 1: Add doc_type column to Document model**

In `app/models/document.py`, add one line after `category` (line 17):

```python
    category: Mapped[str] = mapped_column(String(64), default="未分类", nullable=False, comment="文档分类")
    doc_type: Mapped[str] = mapped_column(String(32), default="general", server_default="'general'", comment="文档结构类型：policy / manual / general")
```

- [ ] **Step 2: Create alembic migration**

Create `alembic/versions/20260510_0008_add_doc_type.py`:

```python
"""add doc_type to documents

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "doc_type",
            sa.String(32),
            nullable=False,
            server_default="'general'",
            comment="文档结构类型：policy / manual / general",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "doc_type")
```

- [ ] **Step 3: Run migration and verify**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m alembic upgrade head
```

Expected: migration runs without error.

- [ ] **Step 4: Verify model imports cleanly**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -c "from app.models.document import Document; print(Document.__table__.columns['doc_type'])"
```

Expected: prints column info for `doc_type`.

- [ ] **Step 5: Commit**

```bash
cd D:\Python\FactoryOffice-Agent-main && git add backend/app/models/document.py backend/alembic/versions/20260510_0008_add_doc_type.py
git commit -m "feat: add doc_type column to Document model"
```

---

### Task 2: Write SplitterConfig + get_config with failing tests

**Files:**
- Create: `tests/test_text_splitter.py` (skeleton + config tests)
- Modify: `app/rag/text_splitter.py` (add config classes, keep existing logic for now)

- [ ] **Step 1: Write failing test for get_config**

Create `tests/test_text_splitter.py`:

```python
import re
import pytest
from app.rag.text_splitter import SplitterConfig, get_config


class TestSplitterConfig:
    def test_get_config_returns_policy_config(self):
        config = get_config("policy")
        assert config.chunk_size == 900
        assert config.overlap == 100

    def test_get_config_returns_manual_config(self):
        config = get_config("manual")
        assert config.chunk_size == 500
        assert config.overlap == 60

    def test_get_config_returns_general_config(self):
        config = get_config("general")
        assert config.chunk_size == 800
        assert config.overlap == 120

    def test_invalid_doc_type_uses_general(self):
        config = get_config("invalid_xyz")
        assert config.chunk_size == 800
        assert config.overlap == 120

    def test_config_heading_pattern_matches_chinese(self):
        config = get_config("policy")
        assert config.heading_pattern.search("## 3. 基本原则")
        assert config.heading_pattern.search("# 采购管理制度")
        assert not config.heading_pattern.search("普通文本行")

    def test_config_table_pattern_matches_markdown_table(self):
        config = get_config("manual")
        assert config.table_pattern.search("| 设备类别 | 设备示例 |")
        assert config.table_pattern.search("|---|---|")
        assert not config.table_pattern.search("普通文本")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/test_text_splitter.py -v
```

Expected: FAIL — `SplitterConfig` and `get_config` not defined (ImportError).

- [ ] **Step 3: Implement SplitterConfig + get_config**

In `app/rag/text_splitter.py`, add at the top (after existing `re` import, before `normalize_text`):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/test_text_splitter.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd D:\Python\FactoryOffice-Agent-main && git add backend/app/rag/text_splitter.py backend/tests/test_text_splitter.py
git commit -m "feat: add SplitterConfig and get_config with three doc-type presets"
```

---

### Task 3: Implement StructuredTextSplitter core logic

**Files:**
- Modify: `app/rag/text_splitter.py` (add boundary detection + `structured_split()` + `_split_by_boundaries()` + `_sliding_window_sentence_aware()`)

- [ ] **Step 1: Extend test file with structure-aware split tests**

Add to `tests/test_text_splitter.py`:

```python
from app.rag.text_splitter import TextChunk, split_text


class TestStructuredSplit:
    def test_empty_text_returns_empty(self):
        result = split_text("", doc_type="general")
        assert result == []

    def test_policy_keeps_sections_together(self):
        text = "## 3. 基本原则\n\n### 3.1 业务必要性原则\n\n采购申请必须基于真实业务需求。申请部门应说明采购用途。"
        chunks = split_text(text, doc_type="policy")
        assert len(chunks) >= 1
        joined = " ".join(c.text for c in chunks)
        assert "基本原则" in joined
        assert "业务必要性原则" in joined
        assert "采购申请必须基于真实业务需求" in joined

    def test_manual_keeps_table_rows_together(self):
        text = """## 2. 适用范围

| 设备类别 | 设备示例 | 责任部门 |
|---|---|---|
| 螺杆式空压机 | AC-A01 | 设备部 |
| 储气罐 | TK-A01 | 设备部 |
| 冷冻式干燥机 | DR-A01 | 设备部 |
| 管路过滤器 | FL-A01 | 设备部 |"""
        chunks = split_text(text, doc_type="manual")
        table_chunks = [c for c in chunks if "|" in c.text]
        assert len(table_chunks) >= 1
        for tc in table_chunks:
            assert "设备类别" in tc.text

    def test_long_paragraph_breaks_at_period(self):
        text = "采购申请必须基于真实业务需求。" * 200
        chunks = split_text(text, doc_type="policy")
        assert len(chunks) > 1
        for chunk in chunks[:-1]:
            assert chunk.text.endswith("。") or chunk.text.endswith("；")

    def test_heading_at_doc_end_not_lost(self):
        text = "正文内容\n\n## 附录"
        chunks = split_text(text, doc_type="general")
        assert any("附录" in c.text for c in chunks)

    def test_chunk_metadata_contains_doc_type(self):
        text = "这是一段测试文本。"
        chunks = split_text(text, doc_type="policy")
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.metadata.get("doc_type") == "policy"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/test_text_splitter.py::TestStructuredSplit -v
```

Expected: FAIL — `split_text()` doesn't accept `doc_type` kwarg yet, or doesn't produce expected results.

- [ ] **Step 3: Rewrite split_text() with structured logic**

Replace the entire content of `app/rag/text_splitter.py` with:

```python
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TextChunk:
    text: str
    index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SplitterConfig:
    chunk_size: int
    overlap: int
    heading_pattern: re.Pattern = field(repr=False)
    table_pattern: re.Pattern = field(repr=False)


POLICY_CONFIG = SplitterConfig(
    chunk_size=900, overlap=100,
    heading_pattern=re.compile(r"^#{1,6}\s"),
    table_pattern=re.compile(r"^\|.*\|"),
)

MANUAL_CONFIG = SplitterConfig(
    chunk_size=500, overlap=60,
    heading_pattern=re.compile(r"^#{1,6}\s"),
    table_pattern=re.compile(r"^\|.*\|"),
)

GENERAL_CONFIG = SplitterConfig(
    chunk_size=800, overlap=120,
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


def normalize_text(text: str) -> str:
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
                current = _maybe_table_block(segment, config)
                if isinstance(current, list):
                    for chunk_text in current:
                        chunks.append(TextChunk(text=chunk_text, index=len(chunks), metadata=dict(base_metadata)))
                    current = ""
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

    for i, line in enumerate(lines):
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


def _maybe_table_block(segment: str, config: SplitterConfig) -> str | list[str]:
    """If segment is a markdown table exceeding chunk_size, split by rows keeping header."""
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
    """Split an over-long paragraph with sentence-boundary-aware sliding window."""
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
```

- [ ] **Step 4: Run all splitter tests**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/test_text_splitter.py -v
```

Expected: 12 passed (6 config + 6 structure).

- [ ] **Step 5: Commit**

```bash
cd D:\Python\FactoryOffice-Agent-main && git add backend/app/rag/text_splitter.py backend/tests/test_text_splitter.py
git commit -m "feat: implement structured text splitter with boundary detection"
```

---

### Task 4: Wire doc_type into upload flow

**Files:**
- Modify: `app/schemas/document.py` (add doc_type to DocumentCreate)
- Modify: `app/services/document_service.py` (pass doc_type to split_text)

- [ ] **Step 1: Add doc_type to DocumentCreate schema**

In `app/schemas/document.py`, in `DocumentCreate` class, add after `uploaded_by`:

```python
    doc_type: str = Field(default="general", max_length=32, description="文档结构类型：policy / manual / general")
```

- [ ] **Step 2: Pass doc_type to split_text in document_service**

In `app/services/document_service.py`, change the `split_text()` call in `index_document_for_knowledge_base()` (line 185-192) from:

```python
    chunks = split_text(
        text,
        metadata={
            "document_id": document.id,
            "filename": document.filename,
            "title": document.title,
            "category": document.category,
        },
    )
```

To:

```python
    chunks = split_text(
        text,
        doc_type=document.doc_type,
        metadata={
            "document_id": document.id,
            "filename": document.filename,
            "title": document.title,
            "category": document.category,
        },
    )
```

- [ ] **Step 3: Verify existing tests still pass**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/test_document_upload.py tests/test_ingest_demo_docs.py -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
cd D:\Python\FactoryOffice-Agent-main && git add backend/app/schemas/document.py backend/app/services/document_service.py
git commit -m "feat: wire doc_type into document upload and indexing flow"
```

---

### Task 5: Wire doc_type into demo ingest script

**Files:**
- Modify: `scripts/ingest_demo_docs.py`

- [ ] **Step 1: Add doc_type inference and pass to split_text**

In `scripts/ingest_demo_docs.py`, add after `infer_content_type()`:

```python
def infer_doc_type(filename: str) -> str:
    mapping = {
        "采购": "policy",
        "差旅": "policy",
        "安全": "policy",
        "设备维修": "manual",
        "质量": "policy",
        "周报": "general",
    }
    for keyword, doc_type in mapping.items():
        if keyword in filename:
            return doc_type
    return "general"
```

In `ingest_one_document()`, update the `Document()` constructor to include `doc_type=infer_doc_type(path.name)`:

```python
        document = Document(
            filename=path.name,
            title=path.stem,
            category=infer_category(path.name),
            doc_type=infer_doc_type(path.name),
            file_path=str(path),
            content_type=infer_content_type(path),
            file_size_bytes=path.stat().st_size,
            file_sha256=digest,
            uploaded_by=None,
        )
```

And update the existing document refresh block to also set `doc_type`:

```python
        document.doc_type = infer_doc_type(path.name)
```

And update the `split_text()` call in `ingest_one_document()` from:

```python
    chunks = split_text(
        text,
        metadata={...},
    )
```

To:

```python
    chunks = split_text(
        text,
        doc_type=document.doc_type,
        metadata={...},
    )
```

- [ ] **Step 2: Run ingest demo docs smoke test**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/test_ingest_demo_docs.py::test_all_demo_docs_can_be_loaded_and_split -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
cd D:\Python\FactoryOffice-Agent-main && git add scripts/ingest_demo_docs.py
git commit -m "feat: wire doc_type into demo document ingest script"
```

---

### Task 6: Full test suite + regression check

**Files:**
- Modify: `tests/test_text_splitter.py` (add final integration-style test)

- [ ] **Step 1: Add demo docs integration test**

Add to `tests/test_text_splitter.py`:

```python
class TestDemoDocsIntegration:
    def test_all_demo_docs_split_with_all_types(self):
        from pathlib import Path
        from app.rag.document_loader import load_document_text

        demo_dir = Path(__file__).resolve().parents[2].parent / "data" / "demo_docs"
        if not demo_dir.exists():
            pytest.skip("demo_docs directory not found")

        doc_types = ["policy", "manual", "general"]
        for path in sorted(demo_dir.glob("*.md")):
            text = load_document_text(path)
            for dt in doc_types:
                chunks = split_text(text, doc_type=dt)
                assert len(chunks) >= 1, f"{path.name} with {dt} should produce chunks"
                for chunk in chunks:
                    assert chunk.metadata.get("doc_type") == dt
                    assert len(chunk.text) > 0
```

- [ ] **Step 2: Run full test suite**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m pytest tests/ -q --ignore=tests/test_ingest_demo_docs.py --ignore=tests/test_seed_demo_data.py
```

Expected: 149 passed (140 + 9 new), 1 skipped.

- [ ] **Step 3: Run alembic downgrade/upgrade smoke test**

```bash
cd D:\Python\FactoryOffice-Agent-main\backend && python -m alembic downgrade -1 && python -m alembic upgrade head
```

Expected: both commands succeed.

- [ ] **Step 4: Final commit**

```bash
cd D:\Python\FactoryOffice-Agent-main && git add backend/tests/test_text_splitter.py && git commit -m "test: add demo docs integration test for structured splitter"
```

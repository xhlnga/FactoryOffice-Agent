"""批量导入 data/demo_docs 下的演示文档。

用法：
    python3 scripts/ingest_demo_docs.py

默认使用本地确定性演示向量，便于没有 Embedding API Key 的环境也能跑通
documents 和 document_chunks 入库流程。若需要调用真实 Embedding API：

    python3 scripts/ingest_demo_docs.py --real-embedding
"""

from __future__ import annotations

import sys
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEMO_DOCS_DIR = PROJECT_ROOT / "data" / "demo_docs"

sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.rag.document_loader import load_document_text  # noqa: E402
from app.rag.embedding_client import demo_embedding, embed_texts  # noqa: E402
from app.rag.text_splitter import split_text  # noqa: E402
from app.rag.vector_store import create_document_chunks  # noqa: E402
from app.utils.file_utils import file_sha256  # noqa: E402


SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".pdf", ".docx"}


def main() -> None:
    """导入 demo 文档并生成切块。"""
    use_real_embedding = "--real-embedding" in sys.argv
    if not DEMO_DOCS_DIR.exists():
        raise SystemExit(f"demo_docs 目录不存在：{DEMO_DOCS_DIR}")

    doc_paths = sorted(
        path
        for path in DEMO_DOCS_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and not path.name.startswith(".")
    )
    if not doc_paths:
        raise SystemExit("未找到可导入的演示文档。")

    try:
        with SessionLocal() as db:
            imported_docs = 0
            imported_chunks = 0
            for path in doc_paths:
                document, chunk_count = ingest_one_document(db, path, use_real_embedding=use_real_embedding)
                imported_docs += 1
                imported_chunks += chunk_count
                print(f"- {document.filename}: {chunk_count} 个切块")
            db.commit()
    except SQLAlchemyError as exc:
        raise SystemExit(
            "\n数据库连接或写入失败。\n"
            "请确认 PostgreSQL 已启动、迁移已执行，并根据运行位置使用正确 DATABASE_URL：\n"
            "- 宿主机运行脚本：postgresql+psycopg://factory_user:factory_pass@localhost:5432/factory_agent\n"
            "- Docker backend 容器内运行：postgresql+psycopg://factory_user:factory_pass@postgres:5432/factory_agent\n"
            f"原始错误：{exc}\n"
        ) from exc

    mode = "真实 Embedding" if use_real_embedding else "本地演示向量"
    print(f"演示文档导入完成：{imported_docs} 份文档，{imported_chunks} 个切块，向量模式：{mode}")


def ingest_one_document(db, path: Path, *, use_real_embedding: bool) -> tuple[Document, int]:
    """导入单个文档，重复执行时会刷新切块。"""
    digest = file_sha256(path)
    document = find_demo_document(db, path, digest)
    if document is None:
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
        db.add(document)
        db.flush()
    else:
        document.filename = path.name
        document.title = path.stem
        document.category = infer_category(path.name)
        document.doc_type = infer_doc_type(path.name)
        document.file_path = str(path)
        document.content_type = infer_content_type(path)
        document.file_size_bytes = path.stat().st_size
        document.file_sha256 = digest
        document.deleted_at = None
        document.chunks.clear()
        db.flush()

    text = load_document_text(path)
    chunks = split_text(
        text,
        doc_type=document.doc_type,
        metadata={
            "filename": path.name,
            "document_title": path.stem,
            "category": document.category,
            "source": "demo_docs",
        },
    )
    embeddings = embed_texts([chunk.text for chunk in chunks]) if use_real_embedding else [
        demo_embedding(chunk.text) for chunk in chunks
    ]
    create_document_chunks(db, document_id=document.id, chunks=chunks, embeddings=embeddings)
    return document, len(chunks)


def find_demo_document(db, path: Path, digest: str) -> Document | None:
    """查找已导入的演示文档。

    优先按哈希匹配；如果演示文档内容被修改，则按文件名匹配并刷新原记录，
    避免同一份制度或手册在知识库中出现多个版本，影响检索可信度。
    """
    document = db.query(Document).filter(Document.file_sha256 == digest).one_or_none()
    if document is not None:
        return document
    return db.query(Document).filter(Document.filename == path.name).one_or_none()


def infer_category(filename: str) -> str:
    """根据文件名推断演示文档分类。"""
    mapping = {
        "采购": "采购流程",
        "差旅": "费用报销",
        "设备维修": "设备手册",
        "质量": "质量流程",
        "安全": "安全规范",
        "周报": "项目文档",
    }
    for keyword, category in mapping.items():
        if keyword in filename:
            return category
    return "演示文档"


def infer_content_type(path: Path) -> str:
    """根据扩展名推断内容类型。"""
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "text/markdown"
    if suffix == ".txt":
        return "text/plain"
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


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


if __name__ == "__main__":
    main()

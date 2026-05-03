import re
from pathlib import Path

from fastapi import status

from app.core.exceptions import AppException


SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".markdown"}


def load_document_text(file_path: str | Path) -> str:
    """根据文件扩展名解析文档为纯文本。"""
    path = Path(file_path)
    if not path.exists():
        raise AppException("文档文件不存在。", status_code=status.HTTP_404_NOT_FOUND)

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise AppException(
            "暂不支持该文档类型。",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"supported_suffixes": sorted(SUPPORTED_SUFFIXES)},
        )

    if suffix == ".pdf":
        return load_pdf_text(path)
    if suffix == ".docx":
        return load_docx_text(path)
    if suffix in {".md", ".markdown"}:
        return load_markdown_text(path)
    return load_plain_text(path)


def load_plain_text(file_path: str | Path) -> str:
    """解析 TXT 文本文件。"""
    return Path(file_path).read_text(encoding="utf-8").strip()


def load_markdown_text(file_path: str | Path) -> str:
    """解析 Markdown 文件，并做轻量标记清理。"""
    text = load_plain_text(file_path)
    return strip_markdown_marks(text)


def load_pdf_text(file_path: str | Path) -> str:
    """解析 PDF 文件。

    需要安装 PyMuPDF。依赖缺失时给出明确提示。
    """
    try:
        import fitz
    except ImportError as exc:
        raise AppException(
            "解析 PDF 需要安装 PyMuPDF。",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="PDF_LOADER_MISSING",
        ) from exc

    pages: list[str] = []
    with fitz.open(file_path) as document:
        for page in document:
            pages.append(page.get_text("text"))
    return "\n\n".join(pages).strip()


def load_docx_text(file_path: str | Path) -> str:
    """解析 DOCX 文件。

    需要安装 python-docx。依赖缺失时给出明确提示。
    """
    try:
        from docx import Document
    except ImportError as exc:
        raise AppException(
            "解析 DOCX 需要安装 python-docx。",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DOCX_LOADER_MISSING",
        ) from exc

    document = Document(file_path)
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n\n".join(paragraphs).strip()


def strip_markdown_marks(text: str) -> str:
    """轻量清理 Markdown 标记，保留原始业务文本。"""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    return text.strip()


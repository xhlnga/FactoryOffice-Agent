import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.core.exceptions import AppException
from app.schemas.document import DocumentRead
from app.services.document_service import save_upload_file, validate_document_filename
from app.utils.file_utils import safe_filename


class FakeUploadFile:
    """测试用上传文件，避免依赖真实 ASGI 文件对象。"""

    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content_type = "text/markdown"
        self._content = content
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._content):
            return b""
        if size is None or size < 0:
            size = len(self._content) - self._offset
        chunk = self._content[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk


class FakeSettings:
    """测试用上传配置。"""

    def __init__(self, upload_dir: Path, *, max_size_bytes: int, chunk_size_bytes: int = 4):
        self.upload_dir = upload_dir
        self.upload_max_size_bytes = max_size_bytes
        self.upload_max_size_mb = 1
        self.upload_chunk_size_bytes = chunk_size_bytes

    def ensure_runtime_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)


class DocumentUploadTest(unittest.TestCase):
    """文档上传相关测试。"""

    def test_safe_filename_blocks_path_traversal(self) -> None:
        self.assertEqual(safe_filename("../采购制度.md"), "采购制度.md")

    def test_validate_document_filename_rejects_unsupported_extension(self) -> None:
        with self.assertRaises(AppException):
            validate_document_filename("设备照片.exe")

    def test_save_upload_file_uses_size_limit_and_cleans_temp_file(self) -> None:
        async def run_case() -> None:
            with tempfile.TemporaryDirectory() as temp_dir:
                upload = FakeUploadFile("设备维修手册.md", b"a" * 12)
                fake_settings = FakeSettings(Path(temp_dir), max_size_bytes=8)

                with patch("app.services.document_service.settings", fake_settings):
                    with self.assertRaises(AppException) as context:
                        await save_upload_file(upload)

                self.assertEqual(context.exception.status_code, 413)
                self.assertEqual(list(Path(temp_dir).iterdir()), [])

        asyncio.run(run_case())

    def test_save_upload_file_returns_hash_and_size(self) -> None:
        async def run_case() -> None:
            with tempfile.TemporaryDirectory() as temp_dir:
                upload = FakeUploadFile("采购管理制度.md", "采购制度".encode("utf-8"))
                fake_settings = FakeSettings(Path(temp_dir), max_size_bytes=1024)

                with patch("app.services.document_service.settings", fake_settings):
                    saved_file = await save_upload_file(upload)

                self.assertTrue(saved_file.path.exists())
                self.assertGreater(saved_file.size_bytes, 0)
                self.assertEqual(len(saved_file.sha256), 64)

        asyncio.run(run_case())

    def test_document_read_does_not_expose_server_file_path(self) -> None:
        """文档 API 响应不应暴露服务器本地绝对路径。"""
        document = SimpleNamespace(
            id=1,
            filename="采购管理制度.md",
            title="采购管理制度",
            category="采购流程",
            file_path="/srv/factory-agent/data/uploads/secret.md",
            content_type="text/markdown",
            file_size_bytes=1024,
            file_sha256="a" * 64,
            uploaded_by=None,
            deleted_at=None,
            created_at=datetime.now(timezone.utc),
        )

        data = DocumentRead.model_validate(document).model_dump(mode="json")

        self.assertNotIn("file_path", data)


if __name__ == "__main__":
    unittest.main()

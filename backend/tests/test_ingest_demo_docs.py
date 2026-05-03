import unittest

from app.rag.document_loader import load_document_text
from app.rag.embedding_client import demo_embedding
from app.rag.text_splitter import split_text
from scripts import ingest_demo_docs


class IngestDemoDocsTest(unittest.TestCase):
    """演示文档解析和切块测试。"""

    def test_demo_docs_directory_has_supported_documents(self) -> None:
        """演示文档目录应包含可导入的制造业文档。"""
        doc_paths = [
            path
            for path in ingest_demo_docs.DEMO_DOCS_DIR.iterdir()
            if path.is_file()
            and path.suffix.lower() in ingest_demo_docs.SUPPORTED_SUFFIXES
            and not path.name.startswith(".")
        ]

        self.assertGreaterEqual(len(doc_paths), 6)

    def test_all_demo_docs_can_be_loaded_and_split(self) -> None:
        """每份 demo 文档都应能解析成文本并切出有效 chunk。"""
        doc_paths = sorted(
            path
            for path in ingest_demo_docs.DEMO_DOCS_DIR.iterdir()
            if path.is_file()
            and path.suffix.lower() in ingest_demo_docs.SUPPORTED_SUFFIXES
            and not path.name.startswith(".")
        )

        for path in doc_paths:
            with self.subTest(filename=path.name):
                text = load_document_text(path)
                chunks = split_text(
                    text,
                    metadata={
                        "filename": path.name,
                        "category": ingest_demo_docs.infer_category(path.name),
                        "source": "demo_docs",
                    },
                )

                self.assertGreater(len(text), 100)
                self.assertTrue(chunks)
                self.assertTrue(all(chunk.text.strip() for chunk in chunks))
                self.assertEqual(chunks[0].metadata["filename"], path.name)

    def test_category_inference_matches_manufacturing_docs(self) -> None:
        """文件名分类应符合当前制造业演示资料。"""
        expected_categories = {
            "采购管理制度.md": "采购流程",
            "差旅报销制度.md": "费用报销",
            "设备维修手册_空压机.md": "设备手册",
            "质量异常处理流程.md": "质量流程",
            "安全生产规范.md": "安全规范",
            "项目周报模板.md": "项目文档",
        }

        for filename, category in expected_categories.items():
            self.assertEqual(ingest_demo_docs.infer_category(filename), category)

    def test_demo_embedding_has_expected_dimension(self) -> None:
        """本地演示向量应与 pgvector 字段维度一致。"""
        vector = demo_embedding("采购金额超过 5 万需要审批。")

        self.assertEqual(len(vector), 1536)
        self.assertGreater(sum(abs(value) for value in vector), 0)

    def test_demo_document_lookup_prefers_hash_then_filename(self) -> None:
        """同名演示文档内容更新时应刷新旧记录，而不是生成重复知识库文档。"""

        class FakeQuery:
            def __init__(self, db) -> None:
                self.db = db

            def filter(self, *_conditions):
                self.db.query_count += 1
                return self

            def one_or_none(self):
                if self.db.query_count == 1:
                    return None
                return self.db.filename_match

        class FakeDbSession:
            def __init__(self) -> None:
                self.query_count = 0
                self.filename_match = object()

            def query(self, _model):
                return FakeQuery(self)

        db = FakeDbSession()
        result = ingest_demo_docs.find_demo_document(
            db,
            ingest_demo_docs.DEMO_DOCS_DIR / "采购管理制度.md",
            "new-digest",
        )

        self.assertIs(result, db.filename_match)
        self.assertEqual(db.query_count, 2)


if __name__ == "__main__":
    unittest.main()

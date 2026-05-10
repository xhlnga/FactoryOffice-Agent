"""重建所有 document_chunks 的 embedding。

使用场景：embedding 模型切换后（如 demo → BGE），
已有向量与新模型不兼容，需全量重建。

运行方式：
  cd backend
  python scripts/reindex_embeddings.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.document_chunk import DocumentChunk
from app.rag.embedding_client import get_embedding_client


def main() -> None:
    client = get_embedding_client()
    db = SessionLocal()
    try:
        chunks = db.query(DocumentChunk).all()
        print(f"找到 {len(chunks)} 个 chunk")

        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.chunk_text for c in batch]
            embeddings = client.embed_batch(texts)
            for chunk, embedding in zip(batch, embeddings):
                chunk.embedding = embedding
            db.commit()
            print(f"已处理 {min(i + batch_size, len(chunks))}/{len(chunks)}")

        print("重建完成。")
    finally:
        db.close()


if __name__ == "__main__":
    main()

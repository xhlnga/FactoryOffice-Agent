from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    """知识库检索请求。"""

    query: str = Field(..., min_length=1, description="用户问题")
    top_k: int = Field(default=5, ge=1, le=20, description="返回片段数量")
    bm25_query: str | None = Field(default=None, description="可选：BM25 关键词搜索用独立查询词")


class Citation(BaseModel):
    """引用来源。"""

    document_id: int | None = Field(default=None, description="文档 ID")
    document_title: str | None = Field(default=None, description="文档标题")
    filename: str | None = Field(default=None, description="文件名")
    chunk_id: int | None = Field(default=None, description="切块 ID")
    chunk_index: int | None = Field(default=None, description="切块序号")
    score: float | None = Field(default=None, description="相关度分数")


class KnowledgeSearchResult(Citation):
    """知识库检索结果。"""

    chunk_text: str = Field(..., description="切块文本")


class KnowledgeSearchResponse(BaseModel):
    """知识库检索响应。"""

    query: str = Field(..., description="用户问题")
    top_k: int = Field(..., description="返回片段数量")
    results: list[KnowledgeSearchResult] = Field(default_factory=list, description="检索结果")
    message: str = Field(..., description="说明信息")


class KnowledgeAskRequest(BaseModel):
    """知识库问答请求。"""

    question: str = Field(..., min_length=1, description="用户问题")
    top_k: int = Field(default=5, ge=1, le=20, description="检索片段数量")


class KnowledgeAskResponse(BaseModel):
    """知识库问答响应。"""

    question: str = Field(..., description="用户问题")
    answer: str = Field(..., description="回答内容")
    citations: list[Citation] = Field(default_factory=list, description="引用来源")
    message: str | None = Field(default=None, description="说明信息")


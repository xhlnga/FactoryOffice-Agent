from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    setup_logging()
    settings.ensure_runtime_dirs()

    app = FastAPI(
        title=settings.app_name,
        description="制造业企业知识库与办公流程智能体后端服务",
        version="1.0.0",
    )

    # 开发环境可按 .env 放开跨域；生产环境会拒绝默认 "*" 配置。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.effective_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    def _on_startup() -> None:
        from app.core.database import SessionLocal
        from app.rag.retriever import init_bm25_index
        db = SessionLocal()
        try:
            init_bm25_index(db)
        finally:
            db.close()

    return app


app = create_app()

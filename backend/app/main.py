from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging


SWAGGER_COLOR_CSS = """
:root {
  --factoryoffice-api-blue: #3b82f6;
  --factoryoffice-api-blue-border: #60a5fa;
  --factoryoffice-api-blue-bg: #eff6ff;
  --factoryoffice-api-red: #ff3b47;
  --factoryoffice-api-red-bg: #fff1f2;
}

.swagger-ui .opblock.opblock-get,
.swagger-ui .opblock.opblock-post,
.swagger-ui .opblock.opblock-put,
.swagger-ui .opblock.opblock-patch,
.swagger-ui .opblock.opblock-options,
.swagger-ui .opblock.opblock-head {
  border-color: var(--factoryoffice-api-blue-border) !important;
  background: var(--factoryoffice-api-blue-bg) !important;
}

.swagger-ui .opblock.opblock-get .opblock-summary,
.swagger-ui .opblock.opblock-post .opblock-summary,
.swagger-ui .opblock.opblock-put .opblock-summary,
.swagger-ui .opblock.opblock-patch .opblock-summary,
.swagger-ui .opblock.opblock-options .opblock-summary,
.swagger-ui .opblock.opblock-head .opblock-summary {
  border-color: var(--factoryoffice-api-blue-border) !important;
}

.swagger-ui .opblock.opblock-get .opblock-summary-method,
.swagger-ui .opblock.opblock-post .opblock-summary-method,
.swagger-ui .opblock.opblock-put .opblock-summary-method,
.swagger-ui .opblock.opblock-patch .opblock-summary-method,
.swagger-ui .opblock.opblock-options .opblock-summary-method,
.swagger-ui .opblock.opblock-head .opblock-summary-method {
  background: var(--factoryoffice-api-blue) !important;
}

.swagger-ui .opblock.opblock-delete {
  border-color: var(--factoryoffice-api-red) !important;
  background: var(--factoryoffice-api-red-bg) !important;
}

.swagger-ui .opblock.opblock-delete .opblock-summary {
  border-color: var(--factoryoffice-api-red) !important;
}

.swagger-ui .opblock.opblock-delete .opblock-summary-method {
  background: var(--factoryoffice-api-red) !important;
}

.swagger-ui .tab li.active:after,
.swagger-ui .tab li.active::after,
.swagger-ui .opblock .tab-header .tab-item.active h4 span:after,
.swagger-ui .opblock .tab-header .tab-item.active h4 span::after {
  background: var(--factoryoffice-api-blue) !important;
}

.swagger-ui .btn.try-out__btn,
.swagger-ui .btn.execute {
  border-color: var(--factoryoffice-api-blue) !important;
  color: var(--factoryoffice-api-blue) !important;
}

.swagger-ui .btn.execute {
  background: var(--factoryoffice-api-blue) !important;
  color: #ffffff !important;
}

.swagger-ui select,
.swagger-ui select:focus,
.swagger-ui input[type="text"],
.swagger-ui input[type="text"]:focus,
.swagger-ui textarea,
.swagger-ui textarea:focus {
  border-color: var(--factoryoffice-api-blue) !important;
  outline-color: var(--factoryoffice-api-blue) !important;
}

.swagger-ui .response-control-media-type__accept-message,
.swagger-ui .response-control-media-type--accept-controller,
.swagger-ui .response-control-media-type--accept-controller small,
.swagger-ui .response-control-media-type--accept-controller p,
.swagger-ui .download-contents {
  color: var(--factoryoffice-api-blue) !important;
}

.swagger-ui .microlight span,
.swagger-ui .highlight-code span,
.swagger-ui .model-example span,
.swagger-ui pre span,
.swagger-ui code span {
  color: #93c5fd !important;
}
"""


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    setup_logging()
    settings.ensure_runtime_dirs()

    app = FastAPI(
        title=settings.app_name,
        description="制造业企业知识库与办公流程智能体后端服务",
        version="1.0.0",
        docs_url=None,
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

    @app.get("/docs", include_in_schema=False)
    def custom_swagger_ui_html() -> HTMLResponse:
        """返回统一蓝色风格的 Swagger UI。

        业务人员看接口文档时，绿色 POST、蓝色 GET、红色 DELETE 混在一起会显得花。
        这里保留 DELETE 红色作为危险动作提示，其余方法统一为蓝色。
        """
        html = get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{settings.app_name} - API Docs",
        )
        body = html.body.decode("utf-8").replace("</head>", f"<style>{SWAGGER_COLOR_CSS}</style></head>")
        return HTMLResponse(body, status_code=html.status_code)

    return app


app = create_app()

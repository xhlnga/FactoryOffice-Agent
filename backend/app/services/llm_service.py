import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import status

from app.core.config import settings
from app.core.exceptions import AppException


def _ensure_llm_config() -> None:
    """检查大模型配置是否完整。"""
    if not settings.llm_base_url or not settings.llm_api_key:
        raise AppException(
            "大模型配置不完整，请检查 LLM_BASE_URL 和 LLM_API_KEY。",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="LLM_CONFIG_MISSING",
        )


def _post_json(url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    """使用标准库发送 JSON POST 请求，避免早期阶段额外增加 HTTP 客户端依赖。"""
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise AppException(
            "大模型服务返回错误。",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="LLM_HTTP_ERROR",
            details={"status_code": exc.code, "response": detail},
        ) from exc
    except URLError as exc:
        raise AppException(
            "无法连接大模型服务。",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="LLM_CONNECTION_ERROR",
            details={"reason": str(exc.reason)},
        ) from exc


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    """调用 OpenAI-compatible chat completions 接口。"""
    _ensure_llm_config()
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model or settings.llm_model,
        "messages": messages,
        "temperature": temperature,
    }
    data = _post_json(url, payload, settings.llm_api_key)

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AppException(
            "大模型响应格式不符合预期。",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="LLM_RESPONSE_INVALID",
            details={"response": data},
        ) from exc


def embedding(text: str, *, model: str | None = None) -> list[float]:
    """调用 OpenAI-compatible embeddings 接口。"""
    if not settings.embedding_base_url or not settings.embedding_api_key:
        raise AppException(
            "Embedding 配置不完整，请检查 EMBEDDING_BASE_URL 和 EMBEDDING_API_KEY。",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="EMBEDDING_CONFIG_MISSING",
        )

    url = f"{settings.embedding_base_url.rstrip('/')}/embeddings"
    payload = {
        "model": model or settings.embedding_model,
        "input": text,
    }
    data = _post_json(url, payload, settings.embedding_api_key)

    try:
        return data["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AppException(
            "Embedding 响应格式不符合预期。",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EMBEDDING_RESPONSE_INVALID",
            details={"response": data},
        ) from exc


from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MAPPING_PATH = Path(__file__).resolve().parents[2] / "data" / "query_rewrite_mapping.json"
_mapping_cache: tuple[float, list[dict[str, str]]] | None = None


def _load_mapping() -> list[dict[str, str]]:
    global _mapping_cache
    try:
        mtime = os.path.getmtime(_MAPPING_PATH)
    except OSError:
        logger.debug("query_rewrite_mapping.json not found at %s", _MAPPING_PATH)
        return []
    if _mapping_cache is not None and _mapping_cache[0] == mtime:
        return _mapping_cache[1]
    try:
        with open(_MAPPING_PATH, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
    except json.JSONDecodeError as exc:
        logger.warning("query_rewrite_mapping.json parse error: %s", exc)
        return []

    try:
        replacements: list[dict[str, str]] = data.get("replacements", [])
        replacements.sort(key=lambda r: len(r["colloquial"]), reverse=True)
        _mapping_cache = (mtime, replacements)
        return replacements
    except KeyError as exc:
        logger.warning("query_rewrite_mapping.json missing key in mapping entry: %s", exc)
        return []


def apply_rules(text: str) -> str:
    # Note: str.replace() runs sequentially, so the output of an earlier
    # rule may match the colloquial pattern of a later rule.
    replacements = _load_mapping()
    result = text
    for rule in replacements:
        result = result.replace(rule["colloquial"], rule["term"])
    return result


def reload_mapping() -> None:
    global _mapping_cache
    _mapping_cache = None


REWRITE_SYSTEM_PROMPT = (
    "你是制造业工厂制度查询助手。把工人说的口语转成规范表达。"
    "只替换用词，不改变原意，不添加额外限定条件。"
    "直接输出改写后的问题，不要解释。"
)


def _call_llm_rewrite(text: str) -> str:
    from app.services.llm_service import chat_completion

    response = chat_completion(
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.1,
    )
    stripped = response.strip()
    if not stripped:
        raise RuntimeError("LLM rewrite returned empty response")
    return stripped


def rewrite_query(original: str) -> str:
    # Step 1: rule-based replacement
    after_rules = apply_rules(original)

    # Step 2: LLM refinement
    try:
        return _call_llm_rewrite(after_rules)
    except Exception as exc:
        logger.warning("LLM rewrite failed, using rule result: %s", exc)
        return after_rules

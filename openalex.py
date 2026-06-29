"""
PubMed 引用数検索システム — OpenAlex API 連携
ジャーナル名から 2yr_mean_citedness（2年平均被引用数）を取得する。
"""

import json
import logging
import os
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

OPENALEX_SOURCES_URL = "https://api.openalex.org/sources"
CACHE_FILE = Path(os.path.dirname(__file__)) / "openalex_cache.json"
CACHE_MAX_AGE_DAYS = 90


def _load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"OpenAlex キャッシュの保存に失敗: {e}")


def _is_cache_fresh(entry: dict) -> bool:
    from datetime import datetime, timedelta
    cached_at = entry.get("cached_at")
    if not cached_at:
        return False
    try:
        dt = datetime.fromisoformat(cached_at)
        return datetime.now() - dt < timedelta(days=CACHE_MAX_AGE_DAYS)
    except ValueError:
        return False


def fetch_citedness(journal_name: str) -> float | None:
    """
    OpenAlex API からジャーナルの 2yr_mean_citedness を取得する。
    結果はローカルファイルにキャッシュされる（90日有効）。

    Args:
        journal_name: ジャーナル名

    Returns:
        2yr_mean_citedness の値。取得失敗時は None。
    """
    if not journal_name or journal_name == "N/A":
        return None

    cache_key = journal_name.strip().lower()
    cache = _load_cache()

    if cache_key in cache and _is_cache_fresh(cache[cache_key]):
        value = cache[cache_key].get("citedness")
        logger.debug(f"OpenAlex キャッシュヒット: {journal_name} → {value}")
        return value

    value = _query_openalex(journal_name)

    from datetime import datetime
    cache[cache_key] = {
        "journal": journal_name,
        "citedness": value,
        "cached_at": datetime.now().isoformat(),
    }
    _save_cache(cache)

    return value


def _query_openalex(journal_name: str) -> float | None:
    """OpenAlex sources API を検索し、最も一致するジャーナルの 2yr_mean_citedness を返す。"""
    params = {
        "search": journal_name,
        "per_page": 5,
        "mailto": "pubmed-citation-alert@example.com",
    }

    try:
        resp = requests.get(OPENALEX_SOURCES_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.warning(f"OpenAlex API リクエスト失敗 ({journal_name}): {e}")
        return None
    finally:
        time.sleep(0.2)

    results = data.get("results", [])
    if not results:
        logger.info(f"OpenAlex: '{journal_name}' に一致するソースなし")
        return None

    journal_lower = journal_name.strip().lower()
    best = None
    for source in results:
        display = (source.get("display_name") or "").strip().lower()
        stats = source.get("summary_stats") or {}
        citedness = stats.get("2yr_mean_citedness")
        if citedness is None:
            continue
        if display == journal_lower:
            logger.info(f"OpenAlex: {journal_name} → 2yr_mean_citedness={citedness:.2f}")
            return round(citedness, 2)
        if best is None:
            best = citedness

    if best is not None:
        logger.info(f"OpenAlex: {journal_name} → 2yr_mean_citedness={best:.2f} (部分一致)")
        return round(best, 2)

    return None

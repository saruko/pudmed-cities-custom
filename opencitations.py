"""
PubMed 引用数急増アラートシステム — OpenCitations COCI API 連携
DOI ベースで引用数の月次差分を算出する。
"""

import time
import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import requests

import config

logger = logging.getLogger(__name__)

COCI_API_BASE = "https://opencitations.net/index/coci/api/v1/citations"


def get_total_citations(doi: str) -> int | None:
    """
    DOI を元に、現在の合計引用数を取得する。

    Args:
        doi: 論文の DOI

    Returns:
        合計引用数。取得失敗時は None。
    """
    if not doi:
        logger.debug("DOI が未指定のためスキップ")
        return None

    citations = _fetch_citations(doi)
    if citations is None:
        return None

    total_count = len(citations)
    logger.info(f"DOI={doi}: 合計引用数={total_count}")
    return total_count


# get_citation_increase は本バージョンでは使用しません。
# 合計引用数の取得には get_total_citations を使用してください。


def _fetch_citations(doi: str) -> list[dict] | None:
    """
    OpenCitations COCI API から引用レコードを取得する。

    Args:
        doi: 論文の DOI

    Returns:
        引用レコードのリスト。失敗時は None。
    """
    url = f"{COCI_API_BASE}/{doi}"

    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"OpenCitations: DOI={doi}, {len(data)} 件の引用レコード取得")
        return data
    except requests.RequestException as e:
        logger.error(f"OpenCitations API リクエスト失敗 (DOI={doi}): {e}")
        return None
    except ValueError as e:
        logger.error(f"OpenCitations JSON パース失敗 (DOI={doi}): {e}")
        return None
    finally:
        # レート制限遵守
        time.sleep(config.OPENCITATIONS_WAIT_SEC)


def _parse_creation_date(creation: str) -> date | None:
    """
    creation フィールドの日付文字列をパースする。

    対応フォーマット:
      - YYYY-MM-DD
      - YYYY-MM（月の1日として扱う）
      - YYYY（年の1月1日として扱う）

    Args:
        creation: 日付文字列

    Returns:
        date オブジェクト。パース不可の場合は None。
    """
    if not creation:
        return None

    parts = creation.strip().split("-")
    try:
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        elif len(parts) == 2:
            # 年月のみ → その月の1日として扱う
            return date(int(parts[0]), int(parts[1]), 1)
        elif len(parts) == 1:
            return date(int(parts[0]), 1, 1)
        else:
            logger.warning(f"不明な日付フォーマット: '{creation}'")
            return None
    except (ValueError, IndexError) as e:
        logger.warning(f"日付パースエラー ('{creation}'): {e}")
        return None

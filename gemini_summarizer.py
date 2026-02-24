"""
PubMed 引用数急増アラートシステム — Gemini API 要約
Gemini API でアブストラクトを日本語要約する。
（google-genai SDK を使用）
"""

import logging
import time

from google import genai

import config

logger = logging.getLogger(__name__)

# 要約プロンプト
SUMMARIZE_PROMPT = (
    "以下の医学論文アブストラクトを3〜5文で日本語要約してください。"
    "専門用語はそのまま使用し、簡潔にまとめてください。\n\n"
)

# リトライ設定
MAX_RETRIES = 3
RETRY_WAIT_SEC = 65      # 429 エラー時の待機秒数（API の指示に合わせて長め）
INTER_REQUEST_WAIT_SEC = 5  # 通常リクエスト間のウェイト（無料枠 15RPM → 最低4秒）

# モデル名
MODEL_NAME = "gemini-2.0-flash"


def _get_client() -> genai.Client:
    """Gemini クライアントを初期化して返す。"""
    return genai.Client(api_key=config.GEMINI_API_KEY)


def summarize_abstract(abstract: str) -> str:
    """
    英語アブストラクトを Gemini API で日本語要約する。

    Args:
        abstract: 英語のアブストラクト

    Returns:
        日本語要約テキスト。エラー時はエラーメッセージ。
    """
    if not abstract or not abstract.strip():
        return "（アブストラクトが存在しないため要約できません）"

    if not config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY が設定されていません")
        return "（Gemini API キーが未設定のため要約をスキップしました）"

    client = _get_client()
    prompt = SUMMARIZE_PROMPT + abstract

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
            summary = response.text.strip()
            logger.info(f"Gemini 要約完了 ({len(summary)} 文字)")
            # リクエスト間のウェイト（レートリミット対策）
            time.sleep(INTER_REQUEST_WAIT_SEC)
            return summary
        except Exception as e:
            err_str = str(e)
            logger.warning(
                f"Gemini API エラー (試行 {attempt}/{MAX_RETRIES}): {e}"
            )
            if attempt < MAX_RETRIES:
                # エラーメッセージから retry 秒数を抽出して待機
                wait_sec = RETRY_WAIT_SEC
                import re
                m = re.search(r"retry in (\d+\.?\d*)s", err_str, re.IGNORECASE)
                if m:
                    wait_sec = float(m.group(1)) + 5  # 少し余裕を持たせる
                logger.info(f"  {wait_sec:.0f} 秒後にリトライします...")
                time.sleep(wait_sec)

    return "（Gemini API による要約に失敗しました）"

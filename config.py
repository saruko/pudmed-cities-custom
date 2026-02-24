"""
PubMed 引用数検索システム — 設定ファイル
"""

import os

# =========================================================
# 検索対象分野（日本語で指定、複数指定可）
# =========================================================
DEFAULT_FIELDS = ['眼科']

# =========================================================
# 論文タイプフィルタ（PubMed Article Type）
# 指定可能値: 'Clinical Trial', 'Meta-Analysis', 'Randomized Controlled Trial',
#              'Review', 'Systematic Review', 'Case Reports', 'Books and Documents'
# 空リスト [] の場合はフィルタなし（全タイプ対象）
# =========================================================
DEFAULT_ARTICLE_TYPES = [
    'Clinical Trial',
    'Meta-Analysis',
    'Randomized Controlled Trial',
    'Review',
    'Systematic Review',
]


# =========================================================
# メール設定（GitHub Secrets / 環境変数から取得）
# =========================================================
GMAIL_ADDRESS = os.environ.get('GMAIL_ADDRESS', '')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', '')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL', '')

# =========================================================
# Gemini API キー（GitHub Secrets / 環境変数から取得）
# =========================================================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# =========================================================
# データベースパス
# =========================================================
DB_PATH = os.environ.get('DB_PATH', 'citation_alerts.db')

# =========================================================
# API リクエスト設定
# =========================================================
PUBMED_WAIT_SEC = 0.35       # PubMed API リクエスト間ウェイト（秒）
OPENCITATIONS_WAIT_SEC = 1.0  # OpenCitations API リクエスト間ウェイト（秒）
